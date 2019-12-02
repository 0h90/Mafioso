class Cop():
    def __init__(self, player_id, player_name):
        self.name = "Cop"
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

        narrator.investigate(self.player_id, act_id)
    
    def get_act_time(self):
        return self.act_time

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("Town Hall", "{}'s last will: {}".format(self.player_name, self.last_will))
        else:
            await narrator.broadcast_message("Town Hall", "{} had no last will.".format(self.player_name))

def whoami():
    me_string = (
        "`Description`: You are a `Cop`! You investigate players. Investigating players reveals their alignment to you on the next morning.\n"
        "`Win Condition`: Lynch all `Mafia`\n"
    )
    return me_string