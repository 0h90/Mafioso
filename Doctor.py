class Doctor():
    def __init__(self):
        self.name = "Doctor"
        self.can_act = True
        self.act_time = "Night"
    
    def act(self, narrator, message):
        save_id = message.mentions[0].id
        narrator.save(save_id) 