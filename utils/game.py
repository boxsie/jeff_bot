import abc
import asyncio
from datetime import datetime

class GuessGame(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, guild_id, on_complete, channel, loop, game_time):
        self.guild_id = guild_id
        self.on_complete = on_complete
        self.channel = channel
        self.started_on = None
        self.finished = False
        self.loop = loop
        self.game_time = game_time
        self.extra_time = 0


    async def time_out(self):
        await asyncio.sleep(self.game_time)

        while self.extra_time > 0:
            et = self.extra_time
            self.game_time += et
            self.extra_time = 0
            await asyncio.sleep(et)

        self.finished = True
        await self.on_complete(self)


    def start(self):
        self.started_on = datetime.now().utcnow()
        self.game_timer = self.loop.create_task(self.time_out())


    def add_time(self, time_to_add):
        self.extra_time += time_to_add


    def time_remaining(self):
        diff = datetime.now().utcnow() - self.started_on
        return (self.game_time + self.extra_time) - diff.total_seconds()


    def finish(self):
        self.finished = True

        if not self.game_timer.cancelled():
             self.game_timer.cancel()


    @abc.abstractmethod
    def set_id(self, game_id):
        """Set the game ID"""
        return


    @abc.abstractmethod
    def set_answer(self, answer_obj):
        """Set the object that contains the answer"""
        return


    @abc.abstractmethod
    def get_answer(self):
        """Return the answer"""
        return


    @abc.abstractmethod
    def make_attempt(self, user_id, guess) -> bool:
        """Make an attempt at the guessing game"""
        return