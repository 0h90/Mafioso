import discord
import time
import asyncio
import re
import os
from collections import defaultdict
import random
from datetime import datetime
from Characters import *

class PlayerManager():
    def __init__(self):
        # Set of player ids
        self.player_set = set()

        # Emoji map
        # Key -> String, common name
        # Val -> Unicode emoji
        self.emoji_map = {
            ":chicken:" : "🐔",
            ":bird:" : "🐦",
            ":baby_chick:" : "🐤",
            ":dog:" : "🐶",
            ":rabbit:" : "🐰",
            ":frog:" : "🐸",
            ":monkey:" : "🐒",
            ":panda_face:" : "🐼",
            ":horse:" : "🐴",
            ":duck:" : "🦆",
            ":snake:" : "🐍",
            ":whale:" : "🐳",
            ":elephant:" : "🐘"
        }

        # Set of allowable characters
        self.character_set = set([
            "Mafia",
            "Doctor",
            "Villager",
            "TownCrier",
            "Cop"
        ])

        # Current amount of each character selected
        # Key -> String, Character name
        # Val -> Int, Count 
        self.character_map = defaultdict(int)

        # Character info
        self.character_info = {
            "Mafia" : Mafia.whoami(),
            "Doctor" : Doctor.whoami(),
            "Villager" : Villager.whoami(),
            "TownCrier" : TownCrier.whoami(),
            "Cop" : Cop.whoami()
        }

        self.total_character_count = 0

        # Map of player ids to character object
        self.player_map = {}

        # Map of player to emojis
        self.player_emoji_map = {}

        # Map of player ids (alive) to character object
        self.alive_players = {}

        # Map of player ids (dead) to character object
        self.dead_players = {}

        # Map of player ids to mafia objects
        self.mafia_map = {}

        # Message manager object
        self.message_manager = None


    def set_message_manager(self, message_manager):
        self.message_manager = message_manager

    def assign_characters_to_players(self):
        # Generate random players
        copied_player_set = self.player_set.copy()
        guild = self.message_manager.get_guild()
        random.seed(os.urandom(1028))

        for char_type, count in self.character_map.items():
            for _ in range(0, count):
                rand_player = copied_player_set.pop()
                print("{} : {}".format(char_type, guild.get_member(rand_player)))
                if char_type == "Doctor":
                    self.player_map[rand_player] = Doctor.Doctor(rand_player, guild.get_member(rand_player).name)
                elif char_type == "Mafia":
                    self.player_map[rand_player] = Mafia.Mafia(rand_player, guild.get_member(rand_player).name)
                    self.mafia_map[rand_player] = self.player_map[rand_player]
                elif char_type == "Villager":
                    self.player_map[rand_player] = Villager.Villager(rand_player, guild.get_member(rand_player).name)
                elif char_type == "Cop":
                    self.player_map[rand_player] = Cop.Cop(rand_player, guild.get_member(rand_player).name)
                elif char_type == "TownCrier":
                    self.player_map[rand_player] = TownCrier.TownCrier(rand_player, guild.get_member(rand_player).name)
        
        self.game_composition = self.player_map.copy()
    
    def assign_emojis_to_players(self):
        allocatable_set = set()
        
        for emoji_name in self.emoji_map:
            allocatable_set.add(emoji_name)
        
        players_to_allocate = self.player_set.copy()

        for _ in range(0, self.get_player_count()):
            curr_player = players_to_allocate.pop()
            self.player_emoji_map[curr_player] = allocatable_set.pop()

    def try_inc_char_count(self, character):
        if self.total_character_count >= len(self.player_set):
            return False

        self.character_map[character] += 1
        return True
    
    def try_dec_char_count(self, character):
        if self.character_map[character] == 0:
            return False

        self.character_map[character] -= 1
        return True

    def get_char_count(self, character):
        return self.character_map[character]

    def add_player(self, player_id):
        self.player_set.add(player_id)

    def remove_player(self, player_id):
        self.player_set.remove(player_id)

    def get_player_set(self):
        return self.player_set
    
    def get_player_count(self):
        return len(self.player_set)
    
    def get_player_map(self):
        return self.player_map

    def get_character_set(self):
        return self.character_set
    
    def get_character_map(self):
        return self.character_map

    def get_player_emoji_map(self):
        return self.player_emoji_map

    def kill_player(self, player_id):
        player_obj = self.alive_players.pop(player_id, None)

        if player_obj is None:
            print("Attempted to kill {} when not in alive list".format(player_id))
            return

        self.dead_players[player_id] = player_obj

    def get_alive(self):
        return self.alive_players

    def get_dead(self):
        return self.dead_players
    
    def get_character_info(self, character):
        return self.character_info[character]