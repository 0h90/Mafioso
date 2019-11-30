import discord
import time
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
import os

class PlayerChannels():
    def __init__(self, act_channel, last_will_channel):
        self.act_channel = act_channel
        self.last_will_channel = last_will_channel
        self.item_channels = []

class ChannelManager():
    def __init__(self, guild):
        # Original game composition
        # Key => Unique user id
        # Value => Role class
        self.game_comp = {}

        # User id to Discord.Member map
        # Key => Unique user id
        # Val => Discord.Member object
        self.player_to_member = {}

        # Alive players_list map
        # Key => Unique user id
        # Value => Role class
        self.alive_players = {}

        # Dead players_list map
        # Key => Unique user id
        # Value => Role class
        self.dead_players = {}
    
        # Alive mafia
        # Key => Unique user id
        # Value => Role class
        self.mafia = {}
    
        # Roles map
        # Key => Role name
        # Value => Discord.Role object
        self.roles = {}

        # The villager channel
        # Where all the announcements go
        self.villager_channel = 0

        # The mafia channel
        self.mafia_channel = 0

        # Where the dead people talk
        self.dead_channel = 0

        # Individual player channels
        # Key => Unique user id
        # Value => PlayerChannels() class
        self.player_channels = {}
    
        self.interaction_manager = InteractionManager()

        self.guild = guild

    def create(self, message, role_dictionary, players_list):
        ## Generate random players_list
        random.seed(os.urandom(200))
        for char_type, count in role_dictionary.items():
            for i in range(0, count):
                rand_player = random.randint(0, len(players_list) - 1)
                print("{} : {}".format(char_type, message.guild.get_member(player_id)))
                player_id = players_list[rand_player]
                member_object = message.guild.get_member(player_id)
                if char_type == "Doctor":
                    self.alive_players[player_id] = Doctor.Doctor(player_id, member_object.name)
                elif char_type == "Mafia":
                    self.alive_players[player_id] = Mafia.Mafia(player_id, member_object.name)
                    self.mafia[player_id] = self.alive_players[player_id]
                elif char_type == "Villager":
                    self.alive_players[player_id] = Villager.Villager(player_id, member_object.name)
                elif char_type == "Cop":
                    self.alive_players[player_id] = Cop.Cop(player_id, member_object.name)
                elif char_type == "TownCrier":
                    self.alive_players[player_id] = TownCrier.TownCrier(player_id, member_object.name)

                self.player_to_member[player_id]  = member_object
                players_list.remove(player_id)
        
        # Copy to game composition
        self.game_comp = self.alive_players.copy()

        # Create roles
        self.roles["Dead"] = await message.guild.create_role(name="Dead")
        self.roles["Day"] = await message.guild.create_role(name="Day")
        self.roles["Night"] = await message.guild.create_role(name="Night")
        self.roles["Alive"] = await message.guild.create_role(name="Alive")

        await self.roles["Alive"].edit(position=1, hoist=True)
        await self.roles["Dead"].edit(position=1, hoist=True)

        # Create permissions and channels
        # Create base permissions
        base_perms = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True)
        
        # Mafia permissions
        mafia_perms = base_perms.copy()
        mafia_perms[self.roles["Alive"]] = discord.PermissionOverwrite(send_messages=True)

        for player_id in self.mafia:
            mafia_perms[message.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)
        
        self.mafia_channel = await message.guild.create_text_channel("mafia", overwrites=mafia_perms)

        # Villager permissions
        villager_perms = base_perms.copy()

        for player_id in self.game_comp:
            villager_perms[message.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)

        villager_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)
        villager_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=False)

        self.villager_channel = await message.guild.create_text_channel("townhall", overwrites=villager_perms)

        dead_perms = base_perms.copy()
        dead_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True,send_messages=True)
        self.dead_channel = await message.guild.create_text_channel("Dead", overwrites=dead_perms)

        # Individual role permissions
        for player_id, role_class in self.game_comp.items():
            if role_class.role_name == "mafia":
                continue
            # Zero out last will and act channel
            last_will_channel = 0
            act_channel = 0

            # Setup a lastwill channel for every player
            last_will_perms = base_perms.copy()
            last_will_perms[message.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)
            last_will_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=True)
            last_will_channel = await message.guild.create_text_channel("lastwill", overwrites=last_will_perms) 
            
            # Setup an act channel if appropriate
            if role_class.can_act is True:
                act_perms = base_perms.copy() 
                act_perms[message.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)
                act_perms[self.roles[role_class.act_time]] = discord.PermissionOverwrite(send_messages=True)
                act_channel = await message.guild.create_text_channel(role_class.role_name, overwrites=act_perms)

            self.player_channels[player_id] = PlayerChannels(last_will_channel, act_channel)
                    
        for player_id, player_chans in self.player_channels.items():
            if player_chans.act_channel != 0:
                await player_chans.act_channel.send("{} You are a {}.\n{}".format(message.guild.get_member(player_id).mention, self.game_comp[player_id].role_name, self.game_comp[player_id].whoami()))
    
    
    async def broadcast_voter_message(self, game_time, message):
        if game_time == "Day":
            self.broadcast_villager_message(message)
        elif game_time == "Night":
            self.broadcast_mafia_message(message)

    async def broadcast_mafia_message(self, message):
        await self.mafia_channel.send(message)

    async def broadcast_villager_message(self, message):
        await self.villager_channel.send(message)

    async def broadcast_individual_messages(self, individual_messages):
        for player_id, message in individual_messages.items():
            await self.player_channels[player_id].act_channel.send(message)
    
    async def update_single_permissions(self, player_id, new_roles):
        member = self.player_to_member[player_id]
        member_roles = member.roles()
        # Remove all game defined roles
        for role in self.roles:
            if role in member_roles:
                member_roles.remove(role)
        # Add newly assigned roles
        for role in new_roles:
            if role not in member_roles:
                member_roles.append(role)
        member.edit(roles=member_roles)
    
    async def update_alive_permissions(self, game_time):
        new_roles = []
        new_roles.append(self.roles[game_time])
        new_roles.append(self.roles["Alive"])

        for player_id in self.alive_players:
            self.update_single_permissions(player_id, new_roles)