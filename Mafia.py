class Mafia():
    def __init__(self):
        self.name = "Mafia"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Mafia"

    def act(self, narrator, message):
        voter_id = message.author.id
        voted_id = message.mentions[0].id
        narrator.add_vote(voter_id, voted_id)
    
    def get_act_time(self):
        return self.act_time