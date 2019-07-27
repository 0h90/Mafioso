class Doctor():
    def __init__(self):
        self.name = "Doctor"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Villager"
    
    def act(self, narrator, message):
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.save(act_id) 
    
    def get_act_time(self):
        return self.act_time