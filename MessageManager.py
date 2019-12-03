import discord
import time
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
from enum import Enum
from ChannelManager import ChannelManager

class GameState(Enum):
    PRE_INIT = 0
    INITIALISE = 1
    STARTED = 2
    FINISHED = 3

class MessageManager():
    def __init__(
        self, 
        self_id, 
        game_admin,
        player_manager):

        # The bot's ID
        self.self_id = self_id 

        # Game admin
        self.game_admin = game_admin

        # Set the game state to the initial state
        self.game_state = GameState.PRE_INIT

        # List of messages to broadcast on time swap
        self.delay_message_list = []

        # Dictionary of key-messages
        # A key-message is any message which produces an event from a reaction
        # Items will be a tuple of:
        # string -> Additional information
        # channel -> Channel object
        self.key_messages = {}
        
        # Command regex
        # (!)(<command>)
        self.regex = re.compile("(^\!)([^ ]+)")
        
        # Default channel to send messages to
        self.init_channel = None

        # Player manager object
        self.player_manager = player_manager

        # Channel manager object
        self.channel_manager = None

    def admin_check(self, player_id):
        if player_id == self.game_admin.id:
            return True
        
        return False

    async def handle_message(self, message):
        result = re.search(self.regex, message.content)
        if result is not None:
            command = result.group(2)

            if command == "help":
                help_msg = (
                    "[*] Misc\n"
                    "`!init` - Initialise and set game players,\n"
                    "`!help` - Display this message.\n"
                    "[*] Gameplay \n"
                    "`!act <number>` - Act on <number\> if your role has the ability to `!act`.\n"
                    "`!lynch <number>` - Vote to lynch a player.\n"
                    "`!abstain` - Abstain from lynching. If you already voted - removes your vote.\n"
                    "`!tovote` - Gets players who have not voted for lynching.\n"
                    "`!timer` - Vote to start a timer which forces a lynch in 1 minute.\n"
                    "`!gamecomp` - List dead players and the game composition.\n"
                    "`!list` - Lists players and their act numbers.\n"
                )
                await message.channel.send(help_msg)
                
            if command == "init":
                if self.game_state != GameState.PRE_INIT:
                    await message.channel.send("Game is already running")
                    return
                self.game_state = GameState.INITIALISE
                self.game_admin = message.author
                self.init_channel = message.channel
                self.guild = message.guild
                self.channel_manager = ChannelManager(message.guild)

                await self.send_init_key_message()

                for character in self.player_manager.get_character_set():
                    await self.send_character_key_message(character)
            
            elif command == "lynch":
                await self.narrator.on_lynch(message)
            
            elif command == "abstain":
                await self.narrator.on_abstain(message)
            
            elif command == "tovote":
                await self.narrator.broadcast_tolynch()
            
            elif command == "gamecomp":
                await self.narrator.broadcast_censoredcomp()
            
            elif command == "list":
                await self.narrator.on_player_list(message)
            
            elif command == "lastwill":
                await self.narrator.on_lastwill(message)

            elif command == "timer":
                async def coroutine():
                    await asyncio.sleep(60)
                    if self.narrator.update_c == 0:
                        await self.narrator.finalise(message)                    
                    return "Done"
                
                if self.narrator.get_time() == "Night":
                    return
                
                self.timer_votes += 1
                print("Curr votes: {}".format(self.timer_votes))
                print ("Returned votes: {} and /2: {}".format(self.narrator.get_alive_count(), (self.narrator.get_alive_count() / 2)))
                if self.timer_votes < (self.narrator.get_alive_count() / 2):
                    await self.narrator.broadcast_message("Town Hall" , "Require: {} more votes".format(math.ceil(self.narrator.get_alive_count() / 2) - self.timer_votes))
                    return
                
                self.timer_votes = 0

                await self.narrator.broadcast_message("Town Hall", "Starting timer, 1 minute until forced lynch.")
                self.narrator.update_c = 0
                asyncio.create_task(coroutine())

            elif command == "reset":
                if message.author == self.game_admin or (self.narrator.is_resettable()):
                    self.game_admin = ""
                    self.being_setup = False
                    self.game_running = False
                    self.characters = defaultdict(int)
                    self.total_players = 0
                    self.participants = []
                    self.get_participants_message = ""
                    old_narrator = self.narrator
                    self.narrator = Narrator.Narrator()
                    await old_narrator.cleanup()
                    self.narrator = Narrator.Narrator()


    async def handle_reaction(self, reaction, player_id):
        if self.game_state == GameState.INITIALISE:
            await self.handle_game_start_reaction(reaction, player_id)
        elif self.game_state == GameState.STARTED:
            await self.handle_game_loop_reaction(reaction, player_id)

    async def handle_game_start_reaction(self, reaction, player_id):
        msg = None
        msg_info = ""
        
        try:
            (msg_info, msg) = self.key_messages[reaction.message.id]
        except KeyError:
            print("Reaction on {}. Not found in key_messages.".format(msg.id))
            return

        if msg_info == "info":
            if reaction.emoji == "✅":
                if player_id not in self.player_manager.get_player_set() and player_id != self.self_id:
                    self.player_manager.add_player(player_id)
                    await msg.edit(content="Current Participants: {}".format(len(self.participants))) 
            elif reaction.emoji == "🟢":
                if self.admin_check(player_id):
                    self.game_state = GameState.STARTED

                    msg = "Total players: {}\n".format(self.player_manager.get_player_count())
                    for character, count in self.player_manager.get_character_map():
                        msg += "Final {} count: {}\n".format(character, count)
                    
                    await self.init_channel.send(msg)
                    await self.narrator.create(message, self.characters, self.participants)
                    
        elif msg_info in self.player_manager.get_character_set():
            if self.admin_check(player_id):
                if str(reaction.emoji) == "⬆":
                    status = self.player_manager.try_inc_char_count(msg_info)
                    if status is False:
                        await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)
                        return
                elif str(reaction.emoji) == "⬇":
                    status = self.player_manager.try_dec_char_count(msg_info)
                    if status is False:
                        await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)
                        return

                edited_message = " ".join(reaction.message.content.split(" ")[:2]) + " " + str(self.player_manager.get_char_count(msg_info))
                await reaction.message.edit(content=edited_message)
                await reaction.message.remove_reaction(str(reaction.emoji), self.game_admin)

    async def send_character_key_message(self, current_type):
        curr_msg = await self.init_channel.send("{} count: {}".format(current_type, self.characters[current_type]))
        self.key_messages[curr_msg.id] = (current_type, curr_msg)
        await curr_msg.add_reaction("⬆")
        await curr_msg.add_reaction("⬇")

    async def send_init_key_message(self):
        curr_msg = await self.init_channel.send("Current Participants: {}".format(len(self.participants)))
        self.key_messages[curr_msg.id] = ("init", curr_msg)
        await curr_msg.add_reaction("✅")
        await curr_msg.add_reaction("🟢")
    
    # TODO: Make argument-less. Just use the reference to ChannelManager
    async def send_welcome_message(self, other_channels, group_channels, private_channels):
        for channel_name, channel_obj in other_channels.items():
            if channel_name == "villager-discussion":
                channel_obj.send("Welcome! This is where all the day-time discussion goes. Have fun!")
            elif channel_name == "dead":
                channel_obj.send("You are dead. You can spectate all the other channels. Don't leak information please.")

        for channel_name, channel_obj in group_channels.items():
            channel_obj.send("Hi @here. You are `{}`.\n{}".format(channel_name, self.player_manager.get_character_info(channel_name)))
        
        for player_id, channel_obj in private_channels.items():
            channel_obj.send("Hi {}. You are a `{}`.\n{}".format(self.guild.get_member(player_id).mention(), channel_obj.name, self.player_manager.get_character_info(channel_obj.name)))

    async def send_private_key_message(self):
        for player_id in self.player_manager.get_alive(): 
        for channel_name, channel_obj in self.channel_manager.get_private_role_channels().items():
            
    def get_guild(self):
        return self.guild