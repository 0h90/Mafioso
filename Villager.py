class Villager():
    def __init__(self):
        self.name = "Villager"
        self.can_act = False
        self.act_time = "Day"
        self.alignment = "Villager"
    
    def act(self, narrator, message):
        return -1
    
    def get_act_time(self):
        return self.act_time