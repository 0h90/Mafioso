class Mafia():
    def __init__(self, player_id, player_name):
        self.name = "Mafia"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Mafia"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name

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
        )
        return me_string