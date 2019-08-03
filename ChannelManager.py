import discord
import time
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
import os
import Mafia
import Cop
import Villager
import Doctor
import TownCrier

class PlayerChannels():
    def __init__(self, act_channel, last_will_channel):
        self.act_channel = act_channel
        self.last_will_channel = last_will_channel

class ChannelManager():
    def __init__(self):
        # Original game composition
        # Key => Unique user id
        # Value => Role class
        self.game_comp = {}

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

    def create(self, message, role_dictionary, players_list):
        ## Generate random players_list
        random.seed(os.urandom(200))
        for char_type, count in role_dictionary.items():
            for i in range(0, count):
                rand_player = random.randint(0, len(players_list) - 1)
                print("{} : {}".format(char_type, message.guild.get_member(players_list[rand_player])))
                if char_type == "Doctor":
                    self.alive_players[players_list[rand_player]] = Doctor.Doctor(players_list[rand_player], message.guild.get_member(players_list[rand_player]).name)
                elif char_type == "Mafia":
                    self.alive_players[players_list[rand_player]] = Mafia.Mafia(players_list[rand_player], message.guild.get_member(players_list[rand_player]).name)
                    self.mafia[players_list[rand_player]] = self.alive_players[players_list[rand_player]]
                elif char_type == "Villager":
                    self.alive_players[players_list[rand_player]] = Villager.Villager(players_list[rand_player], message.guild.get_member(players_list[rand_player]).name)
                elif char_type == "Cop":
                    self.alive_players[players_list[rand_player]] = Cop.Cop(players_list[rand_player], message.guild.get_member(players_list[rand_player]).name)
                elif char_type == "TownCrier":
                    self.alive_players[players_list[rand_player]] = TownCrier.TownCrier(players_list[rand_player], message.guild.get_member(players_list[rand_player]).name)
                players_list.remove(players_list[rand_player])
        
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
        base_perms = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True)
        
        mafia_perms = base_perms.copy()
        mafia_perms[self.roles["Alive"]] = discord.PermissionOverwrite(send_messages=True)

        for player_id in self.mafia:
            mafia_perms[message.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)
        
        self.mafia_channel = await message.guild.create_text_channel("mafia", overwrites=mafia_perms)

        villager_perms = base_perms.copy()

        for player_id in self.game_comp:
            villager_perms[message.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)

        villager_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)
        villager_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=False)

        self.villager_channel = await message.guild.create_text_channel("townhall", overwrites=villager_perms)

        dead_perms = base_perms.copy()
        dead_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True,send_messages=True)
        self.dead_channel = await message.guild.create_text_channel("Dead", overwrites=dead_perms)

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
                    
        for player_id, player_channel_object in self.player_channels.items():
            await player_channel_object.act_channel.send("{} You are a {}.\n{}".format(message.guild.get_member(player_id).mention, self.game_comp[player_id].role_name, self.game_comp[player_id].whoami()))