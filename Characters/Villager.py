class Villager():
    def __init__(self, player_id, player_name):
        self.name = "Villager"
        self.changed_name = self.name
        self.can_act = False
        self.act_times = []
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""
    
    def act(self, narrator, message):
        return -1
    
    def get_act_times(self):
        return self.act_times

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("townhall", "{}'s last will: {}".format(self.player_name, self.last_will))
        else:
            await narrator.broadcast_message("town", "{} had no last will.".format(self.player_name))

def whoami():
    me_string = (
        "`Description`: You are a villager. You try to off the rat mafia hiding amongst you.\n"
        "`Win Condition`: Lynch all mafia.\n"
    )
    return me_string