from utils.game import GuessGame


class GeoSniffGame(GuessGame):
    def __init__(self, guild_id, on_complete, channel, loop, game_time):
        super().__init__(guild_id, on_complete, channel, loop, game_time)
        self.location = None


    def set_id(self, game_id):
        self.game_id = game_id


    def set_answer(self, location):
        self.location = location


    def make_attempt(self, user_id, guess):
        if not self.finished:
            if guess == 'None' or guess == 'none':
                return False

            if guess == self.location.sub_area.lower() or guess == self.location.area.lower() or guess == self.location.country.lower():
                self.finish()
                return True
        return False


    def get_answer(self):
        final = []
        if self.location.sub_area:
            final.append(self.location.sub_area)
        if self.location.area:
            final.append(self.location.area)
        if self.location.country:
            final.append(self.location.country)

        final.append(self.location.to_string())

        return ', '.join(final)