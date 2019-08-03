class Villager():
    def __init__(self, player_id, player_name):
        self.name = "Villager"
        self.changed_name = self.name
        self.can_act = False
        self.act_time = "Day"
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""
    
    def act(self, narrator, message):
        return -1
    
    def get_act_time(self):
        return self.act_time

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("townhall", "{}'s last will: {}".format(self.player_name, self.last_will))
        else:
            await narrator.broadcast_message("town", "{} had no last will.".format(self.player_name))