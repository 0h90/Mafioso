class Cop():
    def __init__(self):
        self.name = "Cop"
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Villager"
        self.need_await = False

    def act(self, narrator, message):
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.investigate(act_id)
    
    def get_act_time(self):
        return self.act_time