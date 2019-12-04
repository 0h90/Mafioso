from . import Character

class Cop(Character.Character):
    def __init__(self, player_id, player_name, emoji):
        self.name = "Cop"
        self.changed_name = self.name
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""
        self.emoji = emoji

def whoami():
    me_string = (
        "`Description`: You are a `Cop`! You investigate players. Investigating players reveals their alignment to you on the next morning.\n"
        "`Win Condition`: Lynch all `Mafia`\n"
    )
    return me_string