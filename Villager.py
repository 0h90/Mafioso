class Villager():
    def __init__(self, player_id, player_name):
        self.name = "Villager"
        self.changed_name = self.name
        self.can_act = False
        self.act_time = "Day"
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
    
    def act(self, narrator, message):
        return -1
    
    def get_act_time(self):
        return self.act_time