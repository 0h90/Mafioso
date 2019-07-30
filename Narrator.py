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

        # Dead players
        # Key => User ID
        # Value => Game Class
        self.dead_players = {}

        # Mafia
        # Key => User ID
        # Value => Game Class
        self.mafia = {}

        # Villagers
        # Key => User ID
        # Value => Game Class
        self.villagers = {}

        # Key => Character name
        # Val => List of channels
        self.night_channels = defaultdict(list)

        self.day_channels = defaultdict(list)

        # Key => Player id
        # Val => Channel they belong to
        self.player_channels = {}

        self.dead_channel = 0

        # The "to_act" count for the current time
        self.to_act = set()

        # Same as to act, but for lynching
        self.to_lynch = set()

        # Timer votes
        self.timers = set()

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

        self.game_composition = {}

        # Set to 0 by the timer feature
        self.update_c = 1

        self.resettable = False

    # To be called after object instantiation
    # Does all the required async initialisation
    async def create(self, message, role_dictionary, players):
        # Set guild
        self.guild = message.guild

        ## Generate random players
        random.seed(os.urandom(50))
        for char_type, count in role_dictionary.items():
            for i in range(0, count):
                rand_player = random.randint(0, len(players) - 1)
                print("{} : {}".format(char_type, message.guild.get_member(players[rand_player])))
                if char_type == "Doctor":
                    self.players[players[rand_player]] = Doctor.Doctor(players[rand_player], message.guild.get_member(players[rand_player]).name)
                elif char_type == "Mafia":
                    self.players[players[rand_player]] = Mafia.Mafia(players[rand_player], message.guild.get_member(players[rand_player]).name)
                    self.mafia[players[rand_player]] = self.players[players[rand_player]]
                elif char_type == "Villager":
                    self.players[players[rand_player]] = Villager.Villager(players[rand_player], message.guild.get_member(players[rand_player]).name)
                elif char_type == "Cop":
                    self.players[players[rand_player]] = Cop.Cop(players[rand_player], message.guild.get_member(players[rand_player]).name)
                elif char_type == "TownCrier":
                    self.players[players[rand_player]] = TownCrier.TownCrier(players[rand_player], message.guild.get_member(players[rand_player]).name)
                players.remove(players[rand_player])
        
        self.game_composition = self.players.copy()

        # Create roles
        self.roles["Dead"] = await message.guild.create_role(name="Dead")
        self.roles["Day"] = await message.guild.create_role(name="Day")
        self.roles["Night"] = await message.guild.create_role(name="Night")
        self.roles["Alive"] = await message.guild.create_role(name="Alive")

        await self.roles["Dead"].edit(position=1, hoist=True)
        await self.roles["Alive"].edit(position=1, hoist=True)

        # Create permissions and channels
        base_perms = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True)
        
        mafia_perms = base_perms.copy()
        mafia_perms[self.roles["Alive"]] = discord.PermissionOverwrite(send_messages=True)

        for player, val in self.mafia.items():
            #print("Mafia: {}".format(message.guild.get_member(player).name))
            mafia_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)

        self.night_channels["Mafia"].append(await message.guild.create_text_channel("Mafia", overwrites=mafia_perms))

        villager_perms = base_perms.copy()

        for player, val in self.players.items():
            villager_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)

        villager_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)
        villager_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=False)

        self.day_channels["Town Hall"].append(message.guild.create_text_channel("Town Hall", overwrites=villager_perms))

        dead_perms = base_perms.copy()
        dead_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True,send_messages=True)
        self.dead_channel = await message.guild.create_text_channel("Dead", overwrites=dead_perms)

        for player, val in self.players.items():
            if val.name == "Mafia":
                continue
            if val.can_act is True:
                curr_perms = base_perms.copy()
                curr_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)
                if val.act_time == "Day":
                    curr_perms[self.roles["Day"]] = discord.PermissionOverwrite(send_messages=True)
                    player_channel = await message.guild.create_text_channel(val.name, overwrites=curr_perms)
                    self.day_channels[val.name].append(player_channel)
                elif val.act_time == "Night":
                    curr_perms[self.roles["Night"]] = discord.PermissionOverwrite(send_messages=True)
                    player_channel = await message.guild.create_text_channel(val.name, overwrites=curr_perms)
                    self.night_channels[val.name].append(player_channel)
                self.player_channels[player] = player_channel
        
        for player_id, channel in self.player_channels.items():
            await channel.send("{} You are a {}.\n{}".format(self.guild.get_member(player_id).mention, self.players[player_id].name, self.players[player_id].whoami()))
        
        await self.update()

    async def assign_role(self, player_id, role_list):
        roles = []
        for role in role_list:
            roles.append(self.roles[role])
        await self.guild.get_member(player_id).edit(roles=roles)
    
    async def broadcast_message(self, channel, message):
        if channel in self.day_channels:
            await (self.day_channels[channel])[0].send(message)
        elif channel in self.night_channels:
            await (self.night_channels[channel])[0].send(message)

    async def broadcast_night_messages(self):
        for player, msg in self.individual_messages.items():
            await self.player_channels[player].send(msg)
        self.individual_messages = {}

    async def update(self):
        win = await self.check_win_condition()
        if win == 1:
            return

        if self.time == "Night":
            self.time = "Day"
            await self.broadcast_message("Town Hall", "@here Rise and shine kids. A new day beckons!")
        elif self.time == "Day":
            self.time = "Night"
            await self.broadcast_message("Town Hall", "@here Time to sleep kids. The mafia are coming out.")

        await self.update_actset()
        await self.update_permissions()

        if self.time == "Day":
            await self.broadcast_night_messages()
            if len(self.narrator_message) > 0:
                await self.broadcast_message("Town Hall", self.narrator_message)
            self.narrator_message = ""
            for name, channel in self.day_channels.items():
                await self.get_players_as_indices(name)
        elif self.time == "Night":
            for name, channel in self.night_channels.items():
                await self.get_players_as_indices(name)
        
        self.save_id = 0
        self.investigate_id = 0

    async def update_actset(self):
        self.to_act = set()
        self.to_lynch = set()
        
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

        self.votes = {}
        
    async def update_permissions(self):
        if self.time == "Day":
            for player, val in self.players.items():
                await self.assign_role(player, ["Alive", "Day"])
        if self.time == "Night":
            for player, val in self.players.items():
                await self.assign_role(player, ["Alive", "Night"])
            
    async def on_act(self, message):
        player_id = message.author.id
        
        if player_id not in self.players:
            return

        print("Currently acting: {}".format(message.guild.get_member(player_id).name))

        acting_entity = self.players[player_id]
        
        if self.time != acting_entity.get_act_time():
            return

        if acting_entity.need_await is True:
            await acting_entity.act(self, message)
        else:
            acting_entity.act(self, message)

        if player_id in self.to_act:
            self.to_act.remove(player_id)
        
        if acting_entity.get_act_time() == "Day":
            await self.day_channels[acting_entity.name].send("Received command from: {}".format(acting_entity.name))
        elif acting_entity.get_act_time() == "Night":
            await self.night_channels[acting_entity.name].send("Received command from: {}".format(self.guild.get_member(player_id).name))

        if len(self.to_act) == 0 and len(self.to_lynch) == 0:
            await self.finalise(message)

    async def on_lynch(self, message):
        if self.time != "Day":
            return
        player_id = message.author.id
        
        if player_id in self.to_lynch:
            self.to_lynch.remove(message.author.id)

        index = int(message.content.split(" ")[1])
        lynch_id = self.get_index_id_map()[index]

        self.votes[player_id] = lynch_id

        await self.broadcast_message("Town Hall", "Received command from: {}".format(self.guild.get_member(player_id).name))
        await self.broadcast_current_votes()
    
        if len(self.to_lynch) == 0:
            await self.finalise(message)
    
    async def on_abstain(self, message):
        if self.time != "Day":
            return
        player_id = message.author.id

        if player_id in self.to_lynch:
            self.to_lynch.remove(message.author.id)
        elif player_id in self.votes:
            self.votes.pop(player_id)
        
        await self.broadcast_message("Town Hall", "{} is abstaining from voting.".format(self.guild.get_member(player_id).name))
        await self.broadcast_current_votes()

        if len(self.to_lynch) == 0:
            await self.finalise(message)

    async def finalise(self, message):
        self.update_c = 1
        if self.time == "Day":
            player_id = self.get_max_vote() 
            if player_id == -1:
                await self.day_channels["Town Hall"].send("There is currently a tie! No one will die")
            else:
                await self.on_kill(player_id, "Lynch")
        if self.time == "Night":
            player_id = self.get_max_vote() 
            if player_id == -1:
                await self.night_channels["Mafia"].send("There is currently a tie! Someone needs to change their vote!")
                return
            else:
                await self.on_kill(player_id, "Mafia")

        await self.update()

    async def broadcast_current_votes(self):
        if len(self.votes) == 0:
            if self.time == "Day":
                await self.broadcast_message("Town Hall", "No votes so far")
                return

        vote_counter = defaultdict(int)
        for key, val in self.votes.items():
            vote_counter[val] += 1

        msg = ""
        for key, val in vote_counter.items():
            curr_msg = self.guild.get_member(key).name + ": " + str(val) + '\n'
            msg += curr_msg

        if self.time == "Day":
            await self.broadcast_message("Town Hall", msg)
        elif self.time == "Night":
            await self.broadcast_message("Mafia", msg)

    def get_max_vote(self):
        if len(self.votes) == 0:
            return -1

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

    async def on_kill(self, player_to_kill, kill_type):
        currmsg = ""
        if self.save_id == player_to_kill:
            self.save_id = 0
            currmsg = "Looks like the doctor did a good job that night!\n"
            self.narrator_message += currmsg
            return
        
        if kill_type == "Mafia":
            await self.broadcast_message("Town Hall", "{}, the {}, was found swimming with the fishies!".format(self.players[player_to_kill].player_name, self.players[player_to_kill].changed_name))
        elif kill_type == "Lynch":
            await self.broadcast_message("Town Hall", "{}, the {}, was lynched!".format(self.players[player_to_kill].player_name, self.players[player_to_kill].changed_name))
        elif kill_type == "Gun":
            await self.broadcast_message("Town Hall", "{}, the {}, was shot!".format(self.players[player_to_kill].player_name, self.players[player_to_kill].changed_name))

        await self.players[player_to_kill].broadcast_will(self)

        if player_to_kill in self.mafia:
            self.mafia.pop(player_to_kill)

        self.dead_players[player_to_kill] = self.players.pop(player_to_kill)

        print("Player dying: {}".format(self.game_composition[player_to_kill].name))

        await self.assign_role(player_to_kill, ["Dead"])
        await self.dead_channel.send("{} You died lul".format(self.guild.get_member(player_to_kill).mention))
    
    def add_vote(self, voter, vote):
        self.votes[voter] = vote

    def save(self, save_id):
        self.save_id = save_id

    def investigate(self, investigator, investigate_id):
        curr_msg = ""

        if investigate_id in self.mafia:
            curr_msg = "You find out that {} is a mafia!".format(self.players[investigate_id].name)
        else:
            curr_msg = "You find out that {} is just yo average villager.".format(self.players[investigate_id].name)

        if len(curr_msg) > 0:
            self.individual_messages[investigator] = curr_msg

    async def cleanup(self):
        for player, channel in self.player_channels.items():
            await channel.delete()
        await self.dead_channel.delete()
        await self.day_channels["Town Hall"].delete()
        await self.night_channels["Mafia"].delete()
        for name, role in self.roles.items():
            await role.delete()
    
    async def check_win_condition(self):
        if len(self.mafia) == 0:
            await self.day_channels["Town Hall"].send("@here Villagers won!")
            await self.broadcast_gamecomp()
            self.resettable = True
            return 1
        elif len(self.mafia) >= (len(self.players) / 2):
            await self.day_channels["Town Hall"].send("@here Mafia won!")
            await self.broadcast_gamecomp()
            self.resettable = True
            return 1
        return 0      

    async def on_player_list(self, message):
        await self.get_players_as_indices(message.channel)
    
    async def get_players_as_indices(self, channel_name):
        player_list = "=============PLAYER LIST=============\n"
        for i, (player, val) in enumerate(self.players.items()):
            curr_str = str(i) + ": " + self.guild.get_member(player).name + '\n'
            player_list += curr_str
            self.index_id_map[i] = player
        player_list += "===================================\n"
        await self.broadcast_message(channel_name, player_list)

    async def broadcast_gamecomp(self):
        game_comp = "==============GAME COMP==============\n"
        for player, val in self.game_composition.items():
            curr_str = self.guild.get_member(player).name + ": " + val.name + '\n'
            game_comp += curr_str
        game_comp += "=====================================\n"
        await self.broadcast_message("Town Hall", game_comp)
    
    async def broadcast_tolynch(self):
        to_vote = "Players who haven't voted:\n"
        for player in self.to_lynch:
            curr_str = self.guild.get_member(player).name + '\n'
            to_vote += curr_str
        if self.time == "Day":
            await self.broadcast_message("Town Hall", to_vote)
    
    async def broadcast_censoredcomp(self):
        role_count_map = defaultdict(int)
        for player, val in self.game_composition.items():
            role_count_map[val.name] += 1
        
        game_comp = "==============GAME COMP==============\n"
        for role_name, count in role_count_map.items():
            curr_str = role_name + ": " + str(count) + '\n'
            game_comp += curr_str
        game_comp += "=====================================\n"

        game_comp += "================DEAD================"
        for played_id, game_class in self.dead_players.items():
            curr_str = self.game_composition[played_id].name + ": " + game_class.changed_name + '\n'
            game_comp += curr_str
        game_comp += "=====================================\n"

        await self.broadcast_message("Town Hall", game_comp)
    
    async def lastwill(self, message):
        player_id = message.author.id
        self.players[player_id].set_will(self, message)

    def get_time(self):
        return self.time
    
    def get_index_id_map(self):
        return self.index_id_map
    
    def get_alive_count(self):
        return len(self.players)

    def is_resettable(self):
        return self.resettable
    
    def clear_reset(self):
        self.resettable = False