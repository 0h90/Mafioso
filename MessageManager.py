import discord
import time
import asyncio
import re
from collections import defaultdict
import random
from datetime import datetime
from enum import Enum
from ChannelManager import ChannelManager
from PlayerManager import PlayerManager
from InteractionManager import InteractionManager
from Misc import *

class MessageManager():
    def __init__(
        self, 
        self_id, 
        game_admin,
        ):

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
        
        # Default channel to send messages to
        self.init_channel = None

        # Player manager object, this is the object that manages players.
        # Assign the player_manager parameter to self.player_manager.
        # This is done by the "=" sign, which assigns the player manager (which manages players).
        # This is also known as the player manager (see the PlayerManager class for more information).
        self.player_manager = None

        # Channel manager object
        self.channel_manager = None

        # Voted
        self.player_vote_map = {}

        # Vote map
        self.vote_count_map = defaultdict(int)

        # Individual role act map
        self.player_act_map = {}

    def admin_check(self, player_id):
        if player_id == self.game_admin.id:
            return True
        
        return False

    async def handle_message(self, message):
        command = message.content.split(" ")[0]

        # if the command is help
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
            
        if command == "!init":
            if self.game_state != GameState.PRE_INIT:
                await message.channel.send("Game is already running")
                return
            self.game_admin = message.author
            self.init_channel = message.channel
            self.guild = message.guild

            # Set game_state to INITIALISE
            self.game_state = GameState.INITIALISE

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
                #
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
            print("Reaction on {}. Not found in key_messages.".format(reaction.message.id))
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

                    self.player_manager = PlayerManager(self)
                    self.player_manager.init_player_characters()
                    self.channel_manager = ChannelManager(self, self.player_manager)
                    self.channel_manager.init()
                    self.interaction_manager = InteractionManager(self, self.player_manager, self.channel_manager) 
                    self.interaction_manager.init()
                    
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
    
    async def handle_game_loop_reaction(self, reaction, player_id):
        msg = None
        msg_info = ""

        try:
            (msg_info, msg) = self.key_messages[reaction.message.id]
        except KeyError:
            print("Reaction on {}. Not found in key_messages.".format(reaction.message.id))

        if msg_info == "vote":
            if not self.verify_appropriate_reaction(player_id, self.player_vote_map, reaction):
                return

            if reaction.emoji == "❌":
                vote_id = self.player_vote_map.pop(player_id)
                self.vote_count_map[vote_id] -= 1
            elif reaction.emoji in self.player_manager.get_alive_unicode_emoji_set():
                choose_id = self.player_manager.get_player_id_from_emoji(reaction.emoji)
                # Add vote to player_vote_map
                self.player_vote_map[player_id] = choose_id
                self.vote_count_map[choose_id] += 1
                msg = "Votes:\n" + self.craft_vote_message()
                await reaction.message.edit(content=msg)
        
        elif msg_info == "act":
            if not self.verify_appropriate_reaction(player_id, self.player_act_map, reaction):
                return

            if reaction.emoji == "❌":
                self.player_act_map.pop(player_id)
            elif reaction.emoji in self.player_manager.get_alive_unicode_emoji_set():
                choose_id = self.player_manager.get_player_id_from_emoji(reaction.emoji)
                self.player_act_map[player_id] = choose_id


    def verify_appropriate_reaction(self, player_id, map_to_verify, reaction):
        if player_id not in map_to_verify and reaction.emoji == "❌":
            await reaction.message.remove_reaction(str(reaction.emoji), self.guild.get_member(player_id))
            return False
        if player_id in map_to_verify and reaction.emoji != "❌":
            await reaction.message.remove_reaction(str(reaction.emoji), self.guild.get_member(player_id))
            await reaction.message.channel.send("{} Please remove your choice before choosing again!".format(self.guild.get_member(player_id).mention()))
            return False

        return True
               
    def craft_vote_message(self):
        msg = ""
        for player_id in self.player_manager.get_alive():
            msg += "{} : {}\n".format(self.guild.get_member(player_id).name, self.vote_count_map[player_id])
        
        return msg

    async def send_character_key_message(self, current_type):
        curr_msg = await self.init_channel.send("{} count: {}".format(current_type, self.characters[current_type]))
        self.key_messages[curr_msg.id] = (current_type, curr_msg)
        await curr_msg.add_reaction("⬆")
        await curr_msg.add_reaction("⬇")

    async def send_init_key_message(self):
        init_help_msg = (
            ":white_check_mark: : Join game\n"
            ":green_circle: : Start game\n")
        await self.init_channel.send(init_help_msg)

        curr_msg = await self.init_channel.send("Current Participants: {}".format(len(self.participants)))
        self.key_messages[curr_msg.id] = ("init", curr_msg)
        await curr_msg.add_reaction("✅")
        await curr_msg.add_reaction("🟢")
    
    # TODO: Make argument-less. Just use the reference to ChannelManager
    async def send_welcome_message(self):
        other_channels = self.channel_manager.get_other_channels()
        group_channels = self.channel_manager.get_group_role_channels()
        private_channels = self.channel_manager.get_private_role_channels()

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
        emoji_map = self.player_manager.get_alive_emoji_map()

        msg = "`Act Pane`\n"
        for player_id, emoji_name in emoji_map.items():
            msg += "{}: {}\n".format(emoji_name, self.guild.get_member(player_id).name)

        unicode_mappings = self.player_manager.get_emoji_unicode_map()
        # TODO: Experiment with adding multiple reactions to a message obj
        # and just sending that
        for _, channel_obj in self.channel_manager.get_private_role_channels().items():
            msg_obj = channel_obj.send(msg)
            for _, emoji_name in emoji_map.items():
                msg_obj.add_reaction(unicode_mappings[emoji_name])

            # Store the msg obj in key_messages
            self.key_messages[msg_obj.id] = ("act", msg_obj)
    
    async def send_group_vote_key_message(self, channel_name, pane_name):
        emoji_map = self.player_manager.get_alive_emoji_map()

        msg = pane_name + "\n"
        for player_id, emoji_name in emoji_map.items():
            msg += "{}: {}\n".format(emoji_name, self.guild.get_member(player_id).name)
        
        unicode_mappings = self.player_manager.get_emoji_unicode_map()
        channel_obj = self.channel_manager.get_channel_by_name(channel_name)

        if channel_obj is None:
            print("Attempt to fetch channel failed: {}".format(channel_name))
            return

        msg_obj = channel_obj.send(msg)

        for _, emoji_name in emoji_map.items():
            msg_obj.add_reaction(unicode_mappings[emoji_name])

        self.key_messages[msg_obj.id] = ("vote", msg_obj)
    
    async def send_to_channel(self, message, channel_name):
        channel_obj = self.channel_manager.get_channel_by_name(channel_name)
        channel_obj.send(message)
    
    def get_guild(self):
        return self.guild

    def get_game_state(self):
        return self.game_state

    def set_game_state(self, new_state):
        self.game_state = new_state