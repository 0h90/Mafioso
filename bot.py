import discord
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime

class MafiaClient(discord.Client):
    def __init__(self):
        super(MafiaClient, self).__init__()
        self.game_running = False
        self.game_admin = 0
        self.regex = ""
        self.characters = defaultdict(int)
        self.messages = defaultdict(str)
        self.types = []
        self.mafia = set()
        self.villagers = set()
        self.total_players = 0
        self.total_villagers = 0
        self.total_mafia = 0
        self.participants = []
        self.mafia_types = set()
        self.villager_types = set() 
        self.get_participants_message = ""
        self.guild = ""
        self.mafia_channels = []
        self.villager_channels = []
        self.lynch_votes = defaultdict(int)
        self.kill_votes = defaultdict(int)
        self.alive_players = set()
        self.dead_players = set() 
        self.day = False
        self.alive_role = ""
        self.dead_role = ""
        self.night_role = ""
        self.day_role = ""
        self.night_role_count = 0
        self.current_act_count = 0
        self.voted_set = set()

    async def on_ready(self):
        print("Logged on as {}!".format(self.user))
        self.regex = re.compile("(^::)([^ ]+)")
        self.being_setup = False
    
    async def assign_roles(self, message):
        for player in self.participants:
            self.alive_players.add(player)
            await message.guild.get_member(player.id).edit(roles=[self.alive_role])
    
    async def kill(self, player_to_kill):
        self.alive_players.remove(player_to_kill)
        self.dead_players.add(player_to_kill)
        await player_to_kill.edit(roles=[self.dead_role])
        if player_to_kill in self.mafia:
            self.mafia.remove(player_to_kill)

    async def night_role_act(self, role, message):


    async def on_reaction_add(self, reaction, user):   
        if not self.being_setup:
            return

        if reaction.message.id == self.get_participants_message.id:
            if reaction.emoji == "✅":
                if user not in self.participants and user != self.user:
                    self.participants.append(user)
                    await self.get_participants_message.edit(content="Current Participants: {}".format(len(self.participants))) 
        elif user == self.game_admin and (str(reaction.emoji) == "⬇" or str(reaction.emoji) == "⬆"):
            current_type = self.messages[reaction.message.id]
            if current_type is not None:
                if str(reaction.emoji) == "⬆":
                    if self.total_players >= len(self.participants):
                        await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)
                        return
                    self.characters[current_type] += 1
                    self.total_players += 1
                    if current_type in self.mafia_types:
                        self.total_mafia += 1
                    else:
                        self.total_villagers += 1
                else:
                    if self.characters[current_type] <= 0:
                        await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)
                        return
                    self.characters[current_type] -= 1
                    self.total_players -= 1
                    if current_type in self.mafia_types:
                        self.total_mafia -= 1
                    else:
                        self.total_villagers -= 1
                print(self.total_mafia)
                print(self.total_villagers)
                edited_message = " ".join(reaction.message.content.split(" ")[:4]) + " " + str(self.characters[current_type])
                await reaction.message.edit(content=edited_message)
                await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)

    async def on_message(self, message):
        result = re.search(self.regex, message.content)
        if result is not None:
            command = result.group(2)

            async def create_message(current_type, is_villager):
                self.types.append(current_type)
                curr_msg = await message.channel.send("Current number of {}: {}".format(current_type, self.characters[current_type]))
                await curr_msg.add_reaction("⬆")
                await curr_msg.add_reaction("⬇")
                self.messages[curr_msg.id] = current_type
                if is_villager is True:
                    self.villager_types.add(current_type)
                else:
                    self.mafia_types.add(current_type)
                
            if command == "start":
                if self.game_running is True:
                    await message.channel.send("Game is already running")
                    return
                self.game_running = True
                self.game_admin = message.author
                self.being_setup = True
                self.get_participants_message = await message.channel.send("Current Participants: {}".format(len(self.participants)))
                roles = message.guild.roles

                for role in roles:
                    print(role.name)
                    if role.name == "Alive":
                        self.alive_role = role
                    if role.name == "Dead":
                        self.dead_role = role
                    if role.name == "Day":
                        self.day_role = role
                    if role.name == "Night":
                        self.night_role = role
                        
                await self.get_participants_message.add_reaction("✅")
                await create_message("Villagers", True)
                await create_message("Mafia", False)
            
            elif command == "fin":
                if message.author != self.game_admin:
                    return
                self.being_setup = False
                await message.channel.send("Total players: {}".format(self.total_players)) 
                for character, count in self.characters.items():
                    await message.channel.send("Total {}: {}".format(character, count))

                ## Generate random mafia
                used_players = []
                random.seed(datetime.now())
                for mafia_type in self.mafia_types:
                    self.night_role_count += 1
                    type_count = self.characters[mafia_type]
                    for i in range(0, type_count):
                        rand_player = random.randint(0, len(self.participants) - 1)
                        self.mafia.add(self.participants[rand_player])
                        used_players.append(self.participants.pop(rand_player))                           
                for villager_type in self.villager_types:
                    if villager_type == "Doctor":
                        self.night_role_count += 1
                    elif villager_type == "Cop":
                        self.night_role_count += 1
                    type_count = self.characters[villager_type]
                    for i in range(0, type_count):
                        rand_player = random.randint(0, len(self.participants) - 1)
                        self.villagers.add(self.participants[rand_player])
                        used_players.append(self.participants.pop(rand_player))
                
                self.participants = used_players

                ## Generate private channel
                overwrites = { message.guild.default_role : discord.PermissionOverwrite(read_messages=False,send_messages=False) }
                
                for player in self.mafia:
                    print("Mafia: {}".format(player.name))
                    overwrites[message.guild.get_member(player.id)] = discord.PermissionOverwrite(read_messages=True)
                
                overwrites[self.alive_role] = discord.PermissionOverwrite(read_messages=False)
                overwrites[self.dead_role] = discord.PermissionOverwrite(send_messages=False)
                overwrites_copy = overwrites.copy()

                for player in self.villagers:
                    overwrites_copy[message.guild.get_member(player.id)] = discord.PermissionOverwrite(read_messages=True)

                overwrites_copy[self.alive_role] = discord.PermissionOverwrite(read_messages=True)
                overwrites_copy[self.dead_role] = discord.PermissionOverwrite(send_messages=False)
                overwrites_copy[self.day_role] = discord.PermissionOverwrite(send_messages=True)
                overwrites_copy[self.night_role] = discord.PermissionOverwrite(send_messages=False)

                await self.assign_roles(message)
                self.mafia_channels.append(await message.guild.create_text_channel("Mafia", overwrites=overwrites))
                self.villager_channels.append(await message.guild.create_text_channel("Town Hall", overwrites=overwrites_copy))

            elif command == "voted":
                msg = "Players who have voted: \n"
                for voters in self.voted_set:
                    msg = msg + voters + "\n"                
                await message.channel.send(msg)

            elif command == "lynch":
                self.lynch_votes[message.author] = message.mentions[0]
                vote_counter = defaultdict(int)

                self.voted_set.add(message.author)

                # Print current votes every lynch
                for key, val in self.lynch_votes.items():
                    vote_counter[val] += 1

                msg = ""
                for key, val in vote_counter.items():
                    msg += "{} : {}".format(key.name, str(val))

                await message.channel.send("Current lynch votes\n{}".format(msg))

                if len(self.lynch_votes) == len(self.alive_players):
                    for key, val in self.lynch_votes.items():
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
                            await message.channel.send("Tie between {} and {}".format(key.name, player_to_kill.name))
                            return

                    self.voted_set = set()
                    await message.channel.send("{} has been lynched.".format(player_to_kill.name))
                    await self.kill(player_to_kill)

            elif command == "kill":
                self.kill_votes[message.author] = message.mentions[0]
                vote_counter = defaultdict(int)

                self.voted_set.add(message.author)
                
                for key,val in self.kill_votes.items():
                    vote_counter[val] += 1

                msg = ""
                for key, val in vote_counter.items():
                    msg += "{} : {}".format(key.name, str(val))

                await message.channel.send("Current kill votes\n{}".format(msg))

                if len(self.kill_votes) == len(self.mafia):
                    for key, val in self.lynch_votes.items():
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
                            await message.channel.send("Tie between {} and {}".format(key.name, player_to_kill.name))
                            return

                    self.voted_set = set()
                    await message.channel.send("{} has been found swimming with the fishies".format(player_to_kill.name))
                    await self.kill(player_to_kill)

            elif command == "secretsauce":
                self.game_running = False
            
            elif command == "ketchup":
                for chan in self.mafia_channels:
                    await chan.delete()
                for chan in self.villager_channels:
                    await chan.delete()


api_file = open("apikey", "r") 
api_key = api_file.read()
print(api_key)
client = MafiaClient()
client.run(api_key)