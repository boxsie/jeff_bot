import asyncio
from datetime import datetime

GAME_TIME = 30

class WtpGame:
    def __init__(self, guild_id, pokemon, on_complete, channel, loop):
        self.guild_id = guild_id
        self.pokemon = pokemon
        self.on_complete = on_complete
        self.channel = channel
        self.started_on = datetime.now().utcnow()
        self.game_timer = loop.create_task(self.time_out())
        self.finished = False


    async def time_out(self):
        await asyncio.sleep(GAME_TIME)

        self.finished = True
        await self.on_complete(self)


    def finish(self):
        self.finished = True

        if not self.game_timer.cancelled():
             self.game_timer.cancel()


    def make_attempt(self, user_id, guess):
        if not self.finished and any(guess == n for n in list(self.pokemon.names.values())):
            self.finish()
            return True

        return False