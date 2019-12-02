class Mafia():
    def __init__(self, player_id, player_name):
        self.name = "Mafia"
        self.changed_name = self.name
        self.can_act = True
        self.act_times = ["night"]
        self.alignment = "Mafia"
        self.need_await = False
        self.player_id = player_id
        self.player_name = player_name
        self.last_will = ""

    def act(self, narrator, message):
        voter_id = message.author.id
        print(message.content)
        index = int(message.content.split(" ")[1])
        act_id = narrator.get_index_id_map()[index]

        narrator.add_vote(voter_id, act_id)
    
    def get_act_times(self):
        return self.act_times

    def set_will(self, message):
        self.last_will = " ".join(message.content.split(" ")[1: ])

    async def broadcast_will(self, narrator):
        if len(self.last_will) > 0:
            await narrator.broadcast_message("Town Hall", "{}'s last will: {}".format(self.player_name, self.last_will))
        else:
            await narrator.broadcast_message("Town Hall", "{} had no last will.".format(self.player_name))

def whoami():
    me_string = (
        "`Description`: You are part of the `Mafia`! As the `Mafia` it is your goal to pretend to be villagers while killing them off.\n"
        "`Other`: A majority vote is required to kill someone.\n"
        "All `Mafia` *must* vote.\n"
        "`Win Condition`: Amount of `Mafia` >= Amount of innoncents"
    )
    return me_string