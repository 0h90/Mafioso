class Doctor():
    def __init__(self):
        self.name = "Doctor"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Villager"
    
    def act(self, narrator, message):
        save_id = message.mentions[0].id
        narrator.save(save_id) 
    
    def get_act_time(self):
        return self.act_time