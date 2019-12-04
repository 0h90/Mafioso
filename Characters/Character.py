from abc import ABC, abstractmethod

class Character(ABC):
    def __init__(self):
        self.player_id = 0
        self.player_name = ""
        self.role_name = ""
        self.changed_role_name = ""
        self.act_times = []
        self.can_vote = True
        self.alignment = "Villager"
        self.last_will = ""
        self.act_alone = True
        self.emoji = 0

    def get_emoji(self):
        return self.emoji

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])
    
    def get_will(self):
        return self.last_will
    
    def get_act_times(self):
        return self.act_times
    
    def can_act(self):
        return (len(self.act_times) > 0)