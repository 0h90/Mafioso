class Mafia():
    def __init__(self):
        self.name = "Mafia"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Mafia"

    def act(self, narrator, message):
        voter_id = message.author.id
        print(message.content)
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.add_vote(voter_id, act_id)
    
    def get_act_time(self):
        return self.act_time