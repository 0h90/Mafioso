from collections import defaultdict

class InteractionManager():
    def __init__(self, channel_manager, game_comp, time):
        self.channel_manager = channel_manager

        self.game_comp = game_comp

        self.alive_players = {}

        self.dead_players = {}

        self.mafia = {}

        self.votes = {}

        self.vote_set = set()

        self.act_set = set()

        self.timer_set = set()

        self.save_set = set()

        self.investigate_set = set()

        self.block_set = set()

        self.individual_msgs = {}

        self.game_time = time

        self.time_limit = 180

        self.finalised = True

    async def finalise(self):
        self.finalised = True
        player_to_kill = self.max_vote()
        if player_to_kill == -1:
            if self.game_time == "Day":
                self.channel_manager.broadcast_villager_message("@here Tie when voting. No one will die.")
            elif self.game_time == "Night":"
                self.channel_manager.broadcast_mafia_message("@here Tie when voting.")
                return
        else:
            await self.try_kill(player_to_kill)
                
        await self.update_time()

    async def update_time(self):
        if self.game_time == "Night":
            self.game_time = "Day"
        elif self.game_time == "Day":
            self.game_time = "Night"
        
        # Reset votes
        self.votes = {}

        # Clear all sets
        self.vote_set = set()
        self.act_set = set()
        self.timer_set = set()
        self.save_set = set()
        self.investigate_set = set()
        self.block_set = set()

        # Update the vote set
        # Night => Mafia
        if self.game_time == "Night":
            for player_id in self.mafia:
                self.vote_set.add(player_id)
        # Day => Everyone alive
        elif self.game_time == "Day":
            for player_id in self.alive_players:
                self.vote_set.add(player_id)

        # Update the act_set
        # Make acting with items separate - do not require player with items to act
        for player_id, role_class in self.alive_players.items():
            if role_class.can_act is True and role_class.act_time == self.game_time:
                self.act_set.add(player_id)
        
        # Update permissions
        self.channel_manager.update_alive_permissions(self.game_time)

    ### Helper functions ###
    def max_vote(self):
        if len(self.votes) == 0:
            return -1

        vote_counter = defaultdict(int)
        for key, val in self.votes.items():
            vote_counter[val] += 1

        max_votes = 0
        player_to_kill = 0
        for key, val in vote_counter.items():
            if val > max_votes:
                player_to_kill = key
                max_votes = val

        # Check for 0 ties
        for key, val in vote_counter.items():
            if val == max_votes and key != player_to_kill:
                return -1

        return player_to_kill