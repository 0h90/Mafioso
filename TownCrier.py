class TownCrier:
    def __init__(self):
        self.name = "TownCrier"
        self.can_act = True
        self.act_time = "Day"
        self.alignment = "Villager"
        self.need_await = True
    
    async def act(self, narrator, message):
        await narrator.broadcast_message("Town Hall", "Town crier: {}".format(" ".join(message.content.split(" ")[1:])))
    
    def get_act_time(self):
        return self.act_time