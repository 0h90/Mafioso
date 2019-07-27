import discord
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime

class Narrator():
    def __init__(self):
        # Guild
        self.guild = 0
        # Roles
        # Key => Role name
        # Value => discord.Role object
        self.roles = {}

        # Players
        # Key => User ID
        # Value => Game Class
        self.players = {}

        # Mafia
        # Key => User ID
        # Value => Game Class
        self.mafia = {}

        # Villagers
        # Key => User ID
        # Value => Game Class
        self.villagers = {}

        self.night_channels = {}

        self.day_channels = {}

        # The "to_act" count for the current time
        self.to_act = set()

        # Same as to act, but for lynching
        self.to_lynch = set()

        # Day: Lynch votes
        # Night: Kill votes
        self.votes = {}

        # Day and Night time
        self.time = "Night"

        # Person who was saved (If there is a doctor)
        self.save_id = 0

        # Person who was investigated (If there is a cop)
        self.investigate_id = 0

        # Narrator message / Log of events
        self.narrator_message = ""

        # Separate messages to send to roles
        self.individual_messages = {}

    # To be called after object instantiation
    # Does all the required async initialisation
    async def create(self, message):
        # Set guild
        self.guild = message.guild

        # Create roles
        self.roles["Dead"] = await message.guild.create_role(name="Dead")
        self.roles["Day"] = await message.guild.create_role(name="Day")
        self.roles["Night"] = await message.guild.create_role(name="Night")

        # Create permissions and channels
        base_perms = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles["Dead"]] = discord.PermissionOverwrite(send_messages=False)
        
        mafia_perms = base_perms.copy()

        for player, val in self.mafia.items():
            print("Mafia: {}".format(player.name))
            mafia_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)
        
        self.night_channels["Mafia"] = await message.guild.create_text_channel("Mafia", overwrites=mafia_perms)

        villager_perms = base_perms.copy()

        for player, val in self.players.items():
            villager_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)

        villager_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)

        self.day_channels["Town Hall"] = await message.guild.create_text_channel("Town Hall", overwrites=villager_perms)

        for player, val in self.players.items():
            if val.can_act is True:
                if val.name == "Mafia":
                    continue
                curr_perms = base_perms.copy()
                curr_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)
                if val.act_time == "Day":
                    curr_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)
                    self.day_channels[val.name] = await message.guild.create_text_channel(val.name, overwrites=curr_perms)
                elif val.act_time == "Night":
                    curr_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=True)
                    self.night_channels[val.name] = await message.guild.create_text_channel(val.name, overwrites=curr_perms)
    

    async def remove_roles(self, player_id):
        await self.guild.get_member(player_id).edit(roles=[])

    async def assign_role(self, player_id, role_name):
        await self.guild.get_member(player_id).edit(roles=[self.roles[role_name]])
    
    async def broadcast_message(self):
        for channel, msg in self.individual_messages.items():
            self.night_channels[channel].send(msg)
        self.day_channels["Town Hall"].send(self.narrator_message)
        self.narrator_message = ""
        self.individual_messages = {}

    async def update(self):
        if self.time == "Night":
            self.time = "Day"
        elif self.time == "Day":
            self.time = "Night"

        await self.update_actset()
        await self.update_permissions()

        await self.broadcast_message()

    async def update_actset(self):
        if self.time == "Night":
            for player, val in self.players.items():
                if val.can_act is True and val.act_time == "Night":
                    self.to_act.add(player)
            self.to_lynch = set()

        elif self.time == "Day":
            for player, val in self.players.items():
                if val.can_act is True and val.act_time == "Day":
                    self.to_act.add(player)
                self.to_lynch.add(player)
        
    async def update_permissions(self):
        if self.time == "Day":
            for player, val in self.players.items():
                self.remove_roles(player)
                self.assign_role(player, "Day")
        if self.time == "Night":
            for player, val in self.players.items():
                self.remove_roles(player)
                self.assign_role(player, "Night")
            
    def on_act(self, message):
        #message.guild.get_member(message.User.id)
        player_id = message.User.id
        if player_id in self.to_act:
            self.to_act.remove(message.User.id)

        acting_entity = self.players[player_id]
        acting_entity.act(self)

        if len(self.to_act) == 0 and len(self.to_lynch) == 0:
            self.finalise(message)

    def on_lynch(self, message):
        player_id = message.User.id
        if player_id in self.to_lynch:
            self.to_lynch.remove(message.User.id)

        lynch_id = message.mentions[0].id
        self.votes[player_id] = lynch_id
        if len(self.to_lynch) == 0:
            self.finalise(message)

    def finalise(self, message):
        if self.time == "Day":
            player_id = self.get_max_vote() 
            if player_id == -1:
                self.day_channels["Town Hall"].send("There is currently a tie! Someone needs to change their vote!")
                return
            else:
                self.on_kill(player_id)
        if self.time == "Night":
            player_id = self.get_max_vote() 
            if player_id == -1:
                self.night_channels["Mafia"].send("There is currently a tie! Someone needs to change their vote!")
                return
            else:
                self.on_kill(player_id)

        self.update()

    def get_max_vote(self):
        vote_counter = defaultdict(int)
        for key, val in self.votes.items():
            vote_counter[val] += 1
        
        maxv = 0
        player_to_kill = 0
        for key, val in vote_counter.items():
            if val > maxv:
                player_to_kill = key
                maxv = val

        # Check for 0 ties
        for key, val in vote_counter.items():
            if val == maxv and key != player_to_kill:
                return -1

        return player_to_kill

    async def on_kill(self, player_to_kill):
        if self.save_id == player_to_kill:
            currmsg = "Looks like the doctor did a good job that night"
            print(currmsg)
            self.narrator_message += currmsg
            return
        print("Killing: {}".format(player_to_kill))
        self.players.pop(player_to_kill)
        self.assign_role(player_to_kill, "Dead")
    
    def add_vote(self, voter, vote):
        self.votes[voter] = vote

    def save(self, save_id):
        self.save_id = save_id

    def investigate(self, investigate_id):
        curr_msg = ""
        if investigate_id in self.mafia:
            curr_msg = "You find out that the person you investigated was mafia!"
        else:
            curr_msg = "You visited a good guy"

        self.individual_messages["Cop"] = curr_msg