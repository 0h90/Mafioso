class TownCrier:
    def __init__(self, player_id, player_name):
        self.name = "TownCrier"
        self.changed_name = self.name
        self.can_act = True
        self.act_time = "Day"
        self.alignment = "Villager"
        self.need_await = True
        self.player_id = player_id
        self.player_name = player_name
    
    async def act(self, narrator, message):
        await narrator.broadcast_message("Town Hall", "Town crier: {}".format(" ".join(message.content.split(" ")[1:])))
    
    def get_act_time(self):
        return self.act_time
    
    def whoami(self):
        me_string = (
            "Type `!act <msg>` to have <msg> anonymously broadcasted in #town-hall.\n"
            "For example, `!act hi` will broadcast `Town Crier: Hi` to #town-hall.\n"
        )
        return me_string