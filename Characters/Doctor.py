from . import Character

class Doctor(Character.Character):
    def __init__(self, player_id, role_name, emoji):
        self.name = "Doctor"
        self.changed_name = self.name
        self.can_act = True
        self.act_times = ["night"]
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id 
        self.role_name = role_name
        self.last_will = ""
        self.emoji = emoji
    
def whoami():
    me_string = (
        "`Description`: You are a `Doctor`! You save lives. Every night, you can choose to save 1 player.\n"
        "Saving a player prevents them from being killed by the `Mafia` on the same night which you saved them.\n"
        "`Win Condition`: Lynch all `Mafia`.\n"
    )
    return me_string