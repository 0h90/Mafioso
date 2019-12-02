from abc import ABC, abstractmethod

class Role(ABC):
    def __init__(self):
        self.player_id = 0
        self.player_name = ""
        self.role_name = ""
        self.changed_role_name = ""
        self.can_act = ""
        self.act_times = []
        self.can_vote = True
        self.alignment = "Villager"
        self.last_will = ""
        self.act_alone = True

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])
    
    def get_will(self):
        return self.last_will
    
    @abstractmethod
    def act(self, narrator, message):
        return NotImplemented