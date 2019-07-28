import discord
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
import Narrator

class MafiaClient(discord.Client):
    def __init__(self):
        super(MafiaClient, self).__init__()
        self.game_running = False
        self.game_admin = 0
        self.regex = ""
        self.characters = defaultdict(int)
        self.messages = defaultdict(str)
        self.total_players = 0
        self.participants = []
        self.get_participants_message = ""
        self.narrator = Narrator.Narrator()

    async def on_ready(self):
        print("Logged on as {}!".format(self.user))
        self.regex = re.compile("(^::)([^ ]+)")
        self.being_setup = False
    
    async def on_reaction_add(self, reaction, user):   
        if not self.being_setup:
            return

        if reaction.message.id == self.get_participants_message.id:
            if reaction.emoji == "✅":
                if user.id not in self.participants and user != self.user:
                    self.participants.append(user.id)
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
                else:
                    if self.characters[current_type] <= 0:
                        await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)
                        return
                    self.characters[current_type] -= 1
                    self.total_players -= 1
                edited_message = " ".join(reaction.message.content.split(" ")[:2]) + " " + str(self.characters[current_type])
                await reaction.message.edit(content=edited_message)
                await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)

    async def on_message(self, message):
        result = re.search(self.regex, message.content)
        if result is not None:
            command = result.group(2)

            async def create_message(current_type):
                curr_msg = await message.channel.send("{} count: {}".format(current_type, self.characters[current_type]))
                await curr_msg.add_reaction("⬆")
                await curr_msg.add_reaction("⬇")
                self.messages[curr_msg.id] = current_type
            
            if command == "help":
                await message.channel.send("```::init - Initialise game players\n\
::start - Start game after initialisation\n\
::destroy - Prematurely destroy anything\n\
::reset - Reset everything\n\
::help - Display this message\n\
::act <number\> - Act on <number\> if your role has the ability to act\n\
::lynch <number\> - Lynch <number\>\n\
::abstain - Abstain from lynching. If you already voted - removes your vote\n\
::tovote - Get players who have not voted for lynching\n\
::gamecomp - Get game composition```")
                
            if command == "init":
                if self.game_running is True:
                    await message.channel.send("Game is already running")
                    return
                self.game_running = True
                self.game_admin = message.author
                self.being_setup = True
                self.get_participants_message = await message.channel.send("Current Participants: {}".format(len(self.participants)))
                        
                await self.get_participants_message.add_reaction("✅")
                await create_message("Villager")
                await create_message("Mafia")
                await create_message("Doctor")
                await create_message("Cop")
                await create_message("TownCrier")
            
            elif command == "start":
                if message.author != self.game_admin:
                    return
                self.being_setup = False
                msg = ""
                msg += "Total players: {}\n".format(self.total_players)
                for character, count in self.characters.items():
                    msg += "Final {} count: {}\n".format(character, count)
                await message.channel.send(msg)
                
                await self.narrator.create(message, self.characters, self.participants)
            
            elif command == "act":
                await self.narrator.on_act(message)

            elif command == "lynch":
                await self.narrator.on_lynch(message)
            
            elif command == "abstain":
                await self.narrator.on_abstain(message)
            
            elif command == "tovote":
                await self.narrator.broadcast_tolynch()
            
            elif command == "gamecomp":
                await self.narrator.broadcast_censoredcomp()

            elif command == "destroy":
                await self.narrator.cleanup()
            
            elif command =="reset":
                self.game_running = False
                self.characters = defaultdict(int)
                self.messages = defaultdict(str)
                self.total_players = 0
                self.participants = []
                self.get_participants_message = ""
                self.narrator = Narrator.Narrator()


api_file = open("apikey", "r") 
api_key = api_file.read()
print(api_key)
client = MafiaClient()
client.run(api_key)