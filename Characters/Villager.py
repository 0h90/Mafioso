class Villager():
    def __init__(self, player_id, player_name, emoji):
        self.name = "Villager"
        self.changed_name = self.name
        self.can_act = False
        self.act_times = []
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""
        self.emoji = emoji
    
def whoami():
    me_string = (
        "`Description`: You are a villager. You try to off the rat mafia hiding amongst you.\n"
        "`Win Condition`: Lynch all mafia.\n"
    )
    return me_string