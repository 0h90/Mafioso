import discord
import time
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
import Mafia
import Cop
import Villager
import Doctor

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

        self.dead_channel = 0

        # The "to_act" count for the current time
        self.to_act = set()

        # Same as to act, but for lynching
        self.to_lynch = set()

        # Day: Lynch votes
        # Night: Kill votes
        self.votes = {}

        # Day and Night time
        self.time = "Day"

        # Person who was saved (If there is a doctor)
        self.save_id = 0

        # Person who was investigated (If there is a cop)
        self.investigate_id = 0

        # Narrator message / Log of events
        self.narrator_message = ""

        # Separate messages to send to roles
        self.individual_messages = {}

        self.index_id_map = {}

    # To be called after object instantiation
    # Does all the required async initialisation
    async def create(self, message, role_dictionary, players):
        # Set guild
        self.guild = message.guild

        ## Generate random players
        random.seed(datetime.now())
        for char_type, count in role_dictionary.items():
            for i in range(0, count):
                rand_player = random.randint(0, len(players) - 1)
                print("{} : {}".format(char_type, message.guild.get_member(players[rand_player])))
                if char_type == "Doctor":
                    self.players[players[rand_player]] = Doctor.Doctor()
                elif char_type == "Mafia":
                    self.players[players[rand_player]] = Mafia.Mafia()
                    self.mafia[players[rand_player]] = self.players[players[rand_player]]
                elif char_type == "Villager":
                    self.players[players[rand_player]] = Villager.Villager()
                elif char_type == "Cop":
                    self.players[players[rand_player]] = Cop.Cop()
                players.remove(players[rand_player])

        # Create roles
        self.roles["Dead"] = await message.guild.create_role(name="Dead")
        self.roles["Day"] = await message.guild.create_role(name="Day")
        self.roles["Night"] = await message.guild.create_role(name="Night")

        # Create permissions and channels
        base_perms = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True,send_messages=False)
        
        mafia_perms = base_perms.copy()

        for player, val in self.mafia.items():
            #print("Mafia: {}".format(message.guild.get_member(player).name))
            mafia_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True,send_messages=True)

        self.night_channels["Mafia"] = await message.guild.create_text_channel("Mafia", overwrites=mafia_perms)

        villager_perms = base_perms.copy()

        for player, val in self.players.items():
            villager_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)

        villager_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)
        villager_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=False)

        self.day_channels["Town Hall"] = await message.guild.create_text_channel("Town Hall", overwrites=villager_perms)

        dead_perms = base_perms.copy()
        dead_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True,send_messages=True)

        self.dead_channel = await message.guild.create_text_channel("Dead", overwrites=dead_perms)

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
        
        help_msg = "``` During the day, villagers vote to lynch a player using ::lynch [number]\n \
During the night, mafia vote to kill a player using ::act [number]\n \
Other roles, such as a doctor/cop act on a player using ::act [number]\n \
Where [number] corresponds to the player to be acted on\n \
Everyone at night must act!```"
        self.narrator_message = help_msg

        await self.broadcast_message()
        
        await self.update()

    async def remove_roles(self, player_id):
        await self.guild.get_member(player_id).edit(roles=[])

    async def assign_role(self, player_id, role_name):
        await self.guild.get_member(player_id).edit(roles=[self.roles[role_name]])
    
    async def broadcast_message(self):
        for channel, msg in self.individual_messages.items():
            await self.night_channels[channel].send(msg)
        await self.day_channels["Town Hall"].send(self.narrator_message)
        self.narrator_message = ""
        self.individual_messages = {}

    async def update(self):
        await self.check_win_condition()

        if self.time == "Night":
            self.time = "Day"
            await self.day_channels["Town Hall"].send("@here Rise and shine kids. A new day beckons!")
        elif self.time == "Day":
            self.time = "Night"
            await self.day_channels["Town Hall"].send("@here Time to sleep kids. The mafia are coming out.")

        await self.update_actset()
        await self.update_permissions()

        if self.time == "Day":
            await self.broadcast_message()
            for channel in self.day_channels:
            await channel.send(self.get_players_as_indices())
        elif self.time == "Night":
            for channel in self.night_channels:
            await channel.send(self.get_players_as_indices())

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
                await self.remove_roles(player)
                await self.assign_role(player, "Day")
        if self.time == "Night":
            for player, val in self.players.items():
                await self.remove_roles(player)
                await self.assign_role(player, "Night")
            
    async def on_act(self, message):
        #message.guild.get_member(message.User.id)
        for p in self.to_act:
            print("{}".format(message.guild.get_member(p).name))
        player_id = message.author.id

        print("Currently acting: {}".format(message.guild.get_member(player_id).name))

        acting_entity = self.players[player_id]
        
        if self.time != acting_entity.get_act_time():
            print("Time mismatch?")
            return

        acting_entity.act(self, message)

        print("Player id: {}".format(player_id))
        print("To act: {}".format(self.to_act))

        if player_id in self.to_act:
            self.to_act.remove(message.author.id)
        
        print("After act: {}".format(self.to_act))

        if len(self.to_act) == 0 and len(self.to_lynch) == 0:
            await self.finalise(message)

    async def on_lynch(self, message):
        if self.time != "Day":
            return
        player_id = message.author.id
        if player_id in self.to_lynch:
            self.to_lynch.remove(message.author.id)

        lynch_id = message.mentions[0].id
        self.votes[player_id] = lynch_id
        if len(self.to_lynch) == 0:
            await self.finalise(message)

    async def finalise(self, message):
        if self.time == "Day":
            player_id = self.get_max_vote() 
            if player_id == -1:
                self.day_channels["Town Hall"].send("There is currently a tie! Someone needs to change their vote!")
                return
            else:
                await self.on_kill(player_id)
        if self.time == "Night":
            player_id = self.get_max_vote() 
            if player_id == -1:
                self.night_channels["Mafia"].send("There is currently a tie! Someone needs to change their vote!")
                return
            else:
                await self.on_kill(player_id)

        await self.update()

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
        
        currmsg = "{} was found swimming with the fishies".format(self.guild.get_member(player_to_kill))
        self.narrator_message += currmsg
        print("Killing: {}".format(player_to_kill))
        if player_to_kill in self.mafia:
            self.mafia.pop(player_to_kill)
        self.players.pop(player_to_kill)


        await self.assign_role(player_to_kill, "Dead")
    
    def add_vote(self, voter, vote):
        self.votes[voter] = vote

    def save(self, save_id):
        self.save_id = save_id

    def investigate(self, investigate_id):
        curr_msg = ""
        print("Mafia: ")
        for p in self.mafia:
            print("{}".format(self.guild.get_member(p).name))

        print(self.mafia)
        print("Inv id: {}".format(investigate_id))
        if investigate_id in self.mafia:
            curr_msg = "You visited a naughty fishy"
        else:
            curr_msg = "You visited a good guy"

        self.individual_messages["Cop"] = curr_msg
    
    async def cleanup(self):
        for name, channel in self.day_channels.items():
            await channel.delete()
        for name, channel in self.night_channels.items():
            await channel.delete()
        await self.dead_channel.delete()
    
    async def check_win_condition(self):
        if len(self.mafia) >= (len(self.players) / 2):
            await self.day_channels["Town Hall"].send("@here Mafia won!")
            time.sleep(5)
            await self.cleanup()        
        elif len(self.mafia) == 0:
            await self.day_channels["Town Hall"].send("@here Villagers won!")
            time.sleep(5)
            await self.cleanup()        
    
    def get_players_as_indices(self):
        player_list = ""
        for i, (player, val) in enumerate(self.players.items()):
            curr_str = str(i) + ": " + self.guild.get_member(player).name + '\n'
            player_list += curr_str
            self.index_id_map[i] = player
        return player_list

    def get_time(self):
        return self.time
    
    def get_index_id_map(self):
        return self.index_id_map