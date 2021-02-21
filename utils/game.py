import abc
import asyncio
from datetime import datetime

class GuessGame(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, guild_id, on_complete, channel, loop, game_time):
        self.guild_id = guild_id
        self.on_complete = on_complete
        self.channel = channel
        self.started_on = datetime.now().utcnow()
        self.game_timer = loop.create_task(self.time_out())
        self.finished = False
        self.game_time = game_time


    async def time_out(self):
        await asyncio.sleep(self.game_time)

        self.finished = True
        await self.on_complete(self)


    def finish(self):
        self.finished = True

        if not self.game_timer.cancelled():
             self.game_timer.cancel()


    @abc.abstractmethod
    def set_answer(self, answer_obj):
        """Set the object that contains the answer"""
        return


    @abc.abstractmethod
    def make_attempt(self, user_id, guess) -> bool:
        """Make an attempt at the guessing game"""
        return