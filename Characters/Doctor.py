class Doctor():
    def __init__(self, player_id, role_name):
        self.name = "Doctor"
        self.changed_name = self.name
        self.can_act = True
        self.act_times = ["night"]
        self.alignment = "Villager"
        self.need_await = False
        self.player_id = player_id 
        self.role_name = role_name
        self.last_will = ""
    
    def act(self, narrator, message):
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.save(act_id) 
    
    def get_act_times(self):
        return self.act_times

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("Town Hall", "{}'s last will: {}".format(self.role_name, self.last_will))
        else:
            await narrator.broadcast_message("Town Hall", "{} had no last will.".format(self.role_name))
    
def whoami():
    me_string = (
        "`Description`: You are a `Doctor`! You save lives. Every night, you can choose to save 1 player.\n"
        "Saving a player prevents them from being killed by the `Mafia` on the same night which you saved them.\n"
        "`Win Condition`: Lynch all `Mafia`.\n"
    )
    return me_string