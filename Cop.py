class Cop():
    def __init__(self):
        self.name = "Cop"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Villager"

    def act(self, narrator, message):
        investigate_id = message.mentions[0]
        narrator.investigate(investigate_id)