from . import Character

class TownCrier(Character.Character):
    def __init__(self, player_id, player_name, emoji):
        self.name = "TownCrier"
        self.changed_name = self.name
        self.can_act = True
        self.act_time = "Day"
        self.alignment = "Villager"
        self.need_await = True
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""
        self.emoji = emoji

def whoami():
    me_string = (
        "`Description`: You are a `Town Crier`! You can broadcast messages anonymously to the town discussion.\n"
        "`Win Condition`: Lynch all `Mafia`.\n"
    )
    return me_string