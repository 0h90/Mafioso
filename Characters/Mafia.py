from . import Character

class Mafia(Character.Character):
    def __init__(self, player_id, player_name, emoji):
        self.name = "Mafia"
        self.changed_name = self.name
        self.can_act = True
        self.act_times = ["night"]
        self.alignment = "Mafia"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""
        self.emoji = emoji

def whoami():
    me_string = (
        "`Description`: You are part of the `Mafia`! As the `Mafia` it is your goal to pretend to be villagers while killing them off.\n"
        "`Other`: A majority vote is required to kill someone.\n"
        "All `Mafia` *must* vote.\n"
        "`Win Condition`: Amount of `Mafia` >= Amount of innoncents"
    )
    return me_string