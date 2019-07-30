class Doctor():
    def __init__(self, player_id, player_name):
        self.name = "Doctor"
        self.changed_name = self.name
        self.can_act = True
        self.act_time = "Night"
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id 
        self.player_name = player_name
        self.last_will = ""
    
    def act(self, narrator, message):
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.save(act_id) 
    
    def get_act_time(self):
        return self.act_time
    
    def whoami(self):
        me_string = (
            "Type `!act <number>` to save a player.\n"
            "For example, `!act 0` will save player 0.\n"
            "Saving a player prevents them from being killed by the mafia on the same night which you saved them.\n"
        )
        return me_string

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("Town Hall", "{}'s last will: {}".format(self.player_name, self.last_will))
        else:
            await narrator.broadcast_message("Town Hall", "{} had no last will.".format(self.player_name))