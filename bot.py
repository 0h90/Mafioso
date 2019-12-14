import discord
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
import Narrator
import time
import threading
import math
from MessageManager import MessageManager
from Misc import GameState

class MafiaClient(discord.Client):
    def __init__(self):
        super(MafiaClient, self).__init__()
        self.message_manager = None
        self.game_state = GameState.PRE_INIT

    async def on_ready(self):

        print("Logged on as {}!".format(self.user))
    
    async def on_reaction_add(self, reaction, user):   
        await self.message_manager.handle_reaction(reaction, user.id)

    async def on_message(self, message):
        if self.game_state == GameState.PRE_INIT:
            tokens = message.content.split(" ")
            if tokens[0] == "!init":
                self.message_manager = MessageManager(self.user.id, message.author.id)
            # the game state is pre_init here
        await self.message_manager.handle_message(message)
    
    def reset(self):
        self.message_manager = None
        self.game_state = GameState.PRE_INIT

api_file = open("apikey", "r") 
api_key = api_file.read()
client = MafiaClient()
client.run(api_key)