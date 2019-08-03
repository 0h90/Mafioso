class Mafia():
    def __init__(self, player_id, player_name):
        self.name = "Mafia"
        self.changed_name = self.name
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Mafia"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""

    def act(self, narrator, message):
        voter_id = message.author.id
        print(message.content)
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.add_vote(voter_id, act_id)
    
    def get_act_time(self):
        return self.act_time

    def whoami(self):
        me_string = (
            "Type `!act <number>` to vote to kill <number>.\n"
            "For example, `!act 0` will vote to kill 0.\n"
            "A majority vote is required to kill someone.\n"
            "All mafia `must` vote.\n"
        )
        return me_string

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("Town Hall", "{}'s last will: {}".format(self.player_name, self.last_will))
        else:
            await narrator.broadcast_message("Town Hall", "{} had no last will.".format(self.player_name))