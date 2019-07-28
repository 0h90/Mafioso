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

        self.game_composition = {}

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
                elif char_type == "TownCrier":
                    self.players[players[rand_player]] = TownCrier.TownCrier()
                players.remove(players[rand_player])
        
        self.game_composition = self.players.copy()

        # Create roles
        self.roles["Dead"] = await message.guild.create_role(name="Dead")
        self.roles["Day"] = await message.guild.create_role(name="Day")
        self.roles["Night"] = await message.guild.create_role(name="Night")
        self.roles["Alive"] = await message.guild.create_role(name="Alive")

        # Create permissions and channels
        base_perms = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
        base_perms[self.roles["Dead"]] = discord.PermissionOverwrite(read_messages=True)
        
        mafia_perms = base_perms.copy()
        mafia_perms[self.roles["Alive"]] = discord.PermissionOverwrite(send_messages=True)

        for player, val in self.mafia.items():
            #print("Mafia: {}".format(message.guild.get_member(player).name))
            mafia_perms[message.guild.get_member(player)] = discord.PermissionOverwrite(read_messages=True)

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
        
        for name, channel in self.night_channels.items():
            await channel.send("@here Your assigned role: {}".format(name))
            await channel.send("You can act on a player.\nEnter `::act number` to act on them.\nFor a description on what acting on someone does - check out #town-hall.")

        for name, channel in self.day_channels.items():
            if name == "Town Hall":
                continue
            await channel.send("@here Your assigned role: {}".format(name))
            if name == "TownCrier":
                await channel.send("You can act.\nEnter `::act [message]` to have [message] broadcasted ANONYMOUSLY in #town-hall.")
        
        help_msg = "``` The aim of the game depends on your alignment. \n \
Mafia win condition: Have number of alive mafia be greater/equal to number of alive villagers \n \
Villager win condition: Lynch all mafia``` \
``` The #town-hall is where the daytime discussion takes place. It is locked during the night.\n \
You will have a dedicated channel for your role. \n \
No channel means you are a peasant villager. \n \
During the day, villagers vote to lynch a player using \n \
::lynch number\n \
During the night, mafia vote to kill a player using \n \
::act number\n \
Other roles, such as a doctor/cop act on a player using \n \
::act number\n \
Where 'number' corresponds to the player to be acted on\n \
Everyone at night must act!``` \
``` Current Roles: (D/N indicates whether they can act during the [D]ay or [N]ight)\n \
V/M indicates whether they belong to [V]illagers or [M]afia\n \
Villager[D/V]: Peasant - can only lynch\n \
Town Crier[D/V]: Talks shit - Acting anonymously broadcasts message to Town Hall\n \
Doctor[N/V]: Acting on someone prevents them from being killed by the mafia at night\n \
Cop[N/V]: Acting on someone reports to the cop the following day about the player's alignment\n \
Mafia[N/M]: Acting on someone casts a vote - whoever has the majority vote will be killed by the following day```"
        await self.broadcast_message("Town Hall", help_msg)
        
        await self.update()

    async def assign_role(self, player_id, role_list):
        roles = []
        for role in role_list:
            roles.append(self.roles[role])
        await self.guild.get_member(player_id).edit(roles=roles)
    
    async def broadcast_message(self, channel, message):
        if channel in self.day_channels:
            await self.day_channels[channel].send(message)
        elif channel in self.night_channels:
            await self.night_channels[channel].send(message)

    async def broadcast_night_messages(self):
        for channel, msg in self.individual_messages.items():
            await self.night_channels[channel].send(msg)
        self.individual_messages = {}

    async def update(self):
        await self.check_win_condition()

        if self.time == "Night":
            self.time = "Day"
            await self.broadcast_message("Town Hall", "@here Rise and shine kids. A new day beckons!")
        elif self.time == "Day":
            self.time = "Night"
            await self.broadcast_message("Town Hall", "@here Time to sleep kids. The mafia are coming out.")

        await self.update_actset()
        await self.update_permissions()

        if self.time == "Day":
            #print("BROADCASTING NIGHT MESSAGES")
            await self.broadcast_night_messages()
            if len(self.narrator_message) > 0:
                await self.broadcast_message("Town Hall", self.narrator_message)
            self.narrator_message = ""
            for name, channel in self.day_channels.items():
                await channel.send(self.get_players_as_indices())
        elif self.time == "Night":
            for name, channel in self.night_channels.items():
                await channel.send(self.get_players_as_indices())
        
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
        if self.time == "Day":
            player_id = self.get_max_vote() 
            if player_id == -1:
                await self.day_channels["Town Hall"].send("There is currently a tie! No one will die")
            else:
                await self.on_kill(player_id)
        if self.time == "Night":
            player_id = self.get_max_vote() 
            if player_id == -1:
                await self.night_channels["Mafia"].send("There is currently a tie! Someone needs to change their vote!")
                return
            else:
                await self.on_kill(player_id)

        await self.update()

    async def broadcast_current_votes(self):
        vote_counter = defaultdict(int)
        if len(self.votes) == 0:
            if self.time == "Day":
                await self.broadcast_message("Town Hall", "No votes so far")
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

    async def on_kill(self, player_to_kill):
        currmsg = ""
        if self.save_id == player_to_kill:
            self.save_id = 0
            currmsg = "Looks like the doctor did a good job that night!\n"
            self.narrator_message += currmsg
            return
        
        if self.time == "Night":
            await self.broadcast_message("Town Hall", "{} was found swimming with the fishies!\n".format(self.guild.get_member(player_to_kill).name))
        elif self.time == "Day":
            await self.broadcast_message("Town Hall", "{} was lynched!".format(self.guild.get_member(player_to_kill).name))

        if player_to_kill in self.mafia:
            self.mafia.pop(player_to_kill)
        self.players.pop(player_to_kill)

        print("Player dying: {}".format(self.guild.get_member(player_to_kill).name))

        await self.assign_role(player_to_kill, ["Dead"])
        await self.dead_channel.send("@here Another one has joined the ranks :)")
    
    def add_vote(self, voter, vote):
        self.votes[voter] = vote

    def save(self, save_id):
        self.save_id = save_id

    def investigate(self, investigate_id):
        curr_msg = ""

        if investigate_id in self.mafia:
            curr_msg = "You find out that {} is a mafia!".format(self.guild.get_member(investigate_id).name)
        else:
            curr_msg = "You find out that {} is just yo average villager.".format(self.guild.get_member(investigate_id).name)

        if len(curr_msg) > 0:
            self.individual_messages["Cop"] = curr_msg

    async def cleanup(self):
        for name, channel in self.day_channels.items():
            await channel.delete()
        for name, channel in self.night_channels.items():
            await channel.delete()
        await self.dead_channel.delete()
        for name, role in self.roles.items():
            await role.delete()
    
    async def check_win_condition(self):
        if len(self.mafia) >= (len(self.players) / 2):
            await self.day_channels["Town Hall"].send("@here Mafia won!")
            await self.broadcast_gamecomp()
            time.sleep(15)
            await self.cleanup()        
        elif len(self.mafia) == 0:
            await self.day_channels["Town Hall"].send("@here Villagers won!")
            await self.broadcast_gamecomp()
            time.sleep(15)
            await self.cleanup()        
    
    def get_players_as_indices(self):
        player_list = "=============PLAYER LIST=============\n"
        for i, (player, val) in enumerate(self.players.items()):
            curr_str = str(i) + ": " + self.guild.get_member(player).name + '\n'
            player_list += curr_str
            self.index_id_map[i] = player
        player_list += "===================================\n"
        return player_list

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
        game_comp = "==============GAME COMP==============\n"
        for player, val in self.game_composition.items():
            role_count_map[val.name] += 1
        
        for role_name, count in role_count_map.items():
            curr_str = role_name + ": " + str(count) + '\n'
            game_comp += curr_str
        game_comp += "=====================================\n"
        await self.broadcast_message("Town Hall", game_comp)

    def get_time(self):
        return self.time
    
    def get_index_id_map(self):
        return self.index_id_map