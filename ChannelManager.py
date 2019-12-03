import discord
import time
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
import os
from enum import Enum

class PlayerChannels():
    def __init__(self, act_channel, last_will_channel):
        self.act_channel = act_channel
        self.last_will_channel = last_will_channel
        self.item_channels = []

class RoleEnums(Enum):
    DAY = "day"
    NIGHT = "night"
    ALIVE = "alive"
    DEAD = "dead"
    
class ChannelManager():
    def __init__(self):
        # Dictionary of town-discussion and dead channels
        # Key -> String, Channel name
        # Val -> Channel obj
        self.other_channels = {}

        # Dictionary of group role channels
        # Key -> String, Character group: Mafia...
        # Val -> Channel obj
        self.group_role_channels = {}

        # Dictionary of private role channels
        # Key -> Int, Player Id
        # Val -> Channel obj, Private role channel
        self.private_role_channels = {}

        # Dictionary of last will channels
        # Key -> Int, Player Id
        # Val -> Channel obj, Private last will channel
        self.last_will_channels = {}

        # Dictionary of lists of special channels
        # Key -> Int, Plyaer Id
        # Val -> List of Channel objs, Special channels for to-be-created roles...
        self.special_channels = {}

        # Dummy channels. Roles which don't act.
        # AKA villagers.
        self.dummy_channels = {}

        # Roles map
        # Key => Role name
        # Value => Discord.Role object
        self.roles = {}

        self.message_manager = None

        self.interaction_manager = None
        
        self.player_manager = None

        self.guild = None

    def init(
        self, 
        message_manager,
        player_manager):

        self.message_manager = message_manager
        self.player_manager = player_manager
        self.guild = message_manager.get_guild()

        # Create roles
        self.create_role(RoleEnums.DAY)
        self.create_role(RoleEnums.NIGHT)
        self.create_role(RoleEnums.DEAD)
        self.create_role(RoleEnums.ALIVE)

        await self.roles[RoleEnums.ALIVE].edit(position=1, hoist=True)
        await self.roles[RoleEnums.DEAD].edit(position=1, hoist=True)

        # Create permissions and channels
        # Create base permissions
        base_perms = { self.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles[RoleEnums.DEAD]] = discord.PermissionOverwrite(read_messages=True)
        
        self.other_channels["villager-discussion"] = self.create_public_channel("villager-discussion", base_perms.copy(), [RoleEnums.DAY])
        self.other_channels["dead"] = self.create_roles_channel("dead", base_perms.copy(), [RoleEnums.DEAD], [RoleEnums.DEAD])

        # Create invidiual channels for acting roles
        for player_id, character_obj in self.player_manager.get_player_map().items():
            if character_obj.act_alone:
                if character_obj.can_act():
                    self.private_role_channels[player_id] = self.create_private_channel(character_obj.role_name, base_perms.copy(), player_id, character_obj.act_times)
                else:
                    self.dummy_channels[player_id] = self.create_private_channel(character_obj.role_name, base_perms.copy(), player_id, [])
            else:
                self.group_role_channels[character_obj.role_name] = self.create_group_channel(character_obj.role_name, base_perms.copy(), character_obj.act_times)
        
        # Create last will channel
        for player_id in self.player_manager.get_player_set():
            self.last_will_channels[player_id] = self.create_private_channel("last-will", base_perms.copy(), player_id, [RoleEnums.NIGHT])
        
        message_manager.send_welcome_message(self.other_channels, self.group_role_channels, self.private_role_channels)

    async def create_role(self, role_name):
        self.roles[role_name] = await self.guild.create_role(name=role_name)

    async def create_public_channel(self, channel_name, overwrite_perms, send_roles):
        player_set = self.player_manager.get_player_set()

        for player_id in player_set:
            overwrite_perms[self.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)

        for role in send_roles:
            overwrite_perms[self.roles[role]] = discord.PermissionOverwrite(send_messages=True)
        return await self.guild.create_text_channel(channel_name, overwrites=overwrite_perms)

    async def create_private_channel(self, channel_name, overwrite_perms, player_id, send_roles):
        overwrite_perms[self.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)

        for role in send_roles:
            overwrite_perms[self.roles[role]] = discord.PermissionOverwrite(send_mesages=True)
        return await self.guild.create_text_channel(channel_name, overwrites=overwrite_perms)

    # Create a channel for a character role
    # Where the character role is expected to interact in a single channel : For example, Mafia
    # -> Character role [character_group] : Mafia, Doctor, Cop...
    async def create_group_channel(self, character_group, overwrite_perms, send_roles):
        player_map = self.player_manager.get_player_map()

        for player_id, character_obj in player_map.items():
            if character_obj.character_name == character_group:
                overwrite_perms[self.guild.get_member(player_id)] = discord.PermissionOverwrite(read_messages=True)

        for role in send_roles:
            overwrite_perms[self.roles[role]] = discord.PermissionOverwrite(send_messages=True) 
        return await self.guild.create_text_channel(character_group, overwrites=overwrite_perms)

    # Create a channel for a 
    # -> Discord role [role_group] : dead, alive, Day...
    async def create_roles_channel(self, channel_name, overwrite_perms, read_roles, send_roles):
        for role in read_roles:
            overwrite_perms[self.roles[role]] = discord.PermissionOverwrite(read_message=True)
        
        for role in send_roles:
            overwrite_perms[self.roles[role]] = discord.PermissionOverwrite(send_messages=True)

        return await self.guild.create_text_channel(channel_name, overwrites=overwrite_perms)

    # Gets a channel by name
    # Only searches through other_channels and group_roles_channels    
    def get_channel_by_name(self, channel_name):
        for name, channel_obj in self.other_channels.items():
            if channel_name == name:
                return channel_obj 
        
        for name, channel_obj in self.group_role_channels.items():
            if channel_name == name:
                return channel_obj
    
    def get_group_role_channels(self):
        return self.group_role_channels

    def get_private_role_channels(self):
        return self.private_role_channels

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
        new_roles.append(self.roles["alive"])

        for player_id in self.alive_players:
            self.update_single_permissions(player_id, new_roles)