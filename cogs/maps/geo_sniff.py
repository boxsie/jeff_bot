import os
import discord
import asyncio
import httpx
import json

from os.path import dirname
from datetime import datetime
from utils.game import GuessGame
from discord.ext import commands
from urllib.parse import urljoin
from cogs.maps.geo_sniff_game import GeoSniffGame
from cogs.maps.location import Location
from cogs.maps.street_view import StreetView
from texttable import Texttable

GAME_TIME = 90
CLUE_TIME = 30
ALLOWED_CLUE_TIME = 10
CLUE_RADIUS = 2
MAX_CLUES = 3
GAME_NAME = 'geosniff'

HEADERS = {'Content-type':'application/json', 'Accept':'application/json'}

class GeoSniff(commands.Cog):
    def __init__(self, bot, geo_sniff_api_url, geo_score_api_url, google_api_token):
        self.bot = bot
        self.geo_sniff_api_url = geo_sniff_api_url
        self.geo_score_api_url = geo_score_api_url
        self.current_games = []
        self.street_view = StreetView(geo_sniff_api_url, google_api_token)


    def _get_game_in_progress(self, guild_id):
        return next((g for g in self.current_games if g.guild_id == guild_id), None)


    async def _start_game(self, ctx):
        print(f'Starting Geo Sniff.....')

        game = GeoSniffGame(
            guild_id=ctx.guild.id,
            on_complete=self._finish_game,
            channel=ctx.channel,
            loop=self.bot.loop,
            game_time=GAME_TIME
        )

        self.current_games.append(game)
        await ctx.send(f'Jeff is sniffing one out...')

        loc = await self.street_view.get_random_location()

        game.set_answer(location=loc)

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.geo_sniff_api_url, headers=HEADERS, data=json.dumps({
                'gameName': GAME_NAME,
                'discordId': ctx.message.author.id,
                'correctAnswer': game.get_answer()
            }))
            game.set_id(resp.json())

        img_grid_bytes = await self.street_view.create_img_grid(loc)

        print(f'Geo Sniff Jeff has arrived at {game.get_answer()}')

        await ctx.channel.send(
            content='**Where is Jeff?**',
            file=discord.File(img_grid_bytes, 'where-is-jeff.png')
        )

        game.start()


    async def _make_attempt(self, ctx, game, guess):
        print(f'User {ctx.message.author.id} has guessed {guess}')

        result = game.make_attempt(
            user_id=ctx.message.author.id,
            guess=guess.lower()
        )

        if result:
            await self._finish_game(
                game=game,
                winning_user=ctx.message.author.name
            )
        else:
            await ctx.message.add_reaction('\N{THUMBS DOWN SIGN}')

        async with httpx.AsyncClient() as client:
            resp = await client.post(f'{self.geo_sniff_api_url}/guess', headers=HEADERS, data=json.dumps({
                'gameId': game.game_id,
                'discordId': ctx.message.author.id,
                'attempt': guess.lower(),
                'correct': result
            }))


    async def _get_clue(self, ctx, game):
        game.add_clue()
        game.add_time(CLUE_TIME)

        await ctx.channel.send(f'''**{ctx.message.author.name}** stinks and needs a clue\n{CLUE_TIME} seconds have been added\nJeff is sniffing one out...''')

        loc = await self.street_view.find_random_street_view_loc(
            starting_loc=game.location,
            radius=CLUE_RADIUS
        )

        if loc == None:
            await ctx.send(f'Jeff couldn\'t sniff out clue :(')
            return

        img_grid_bytes = await self.street_view.create_img_grid(loc)
        clue_delta = self.street_view.get_distance(game.location, loc)

        await ctx.channel.send(
            content=f'**Jeff has moved {clue_delta:.2f} km**',
            file=discord.File(img_grid_bytes, 'where-is-jeff.png')
        )


    async def _finish_game(self, game, winning_user=None):
        self.current_games.remove(game)

        if winning_user:
            await game.channel.send(f'**{winning_user}** is the very best!')

        await game.channel.send(f'Jeff was in...\n**{game.get_answer()}**')

        async with httpx.AsyncClient() as client:
            resp = await client.put(f'{self.geo_sniff_api_url}/{game.game_id}', headers=HEADERS)

        print(f'Geo Sniff game complete!')


    @commands.command(name='sniff', help='Start a round of Geo Sniff!')
    async def sniff(self, ctx, guess=None):
        current_game = self._get_game_in_progress(ctx.guild.id)

        if current_game and not guess:
            await ctx.channel.send('There is already a game in progress!')
            return

        if not current_game and guess:
            await ctx.channel.send('There\'s no game to guess on mate')
            return

        if current_game and guess:
            await self._make_attempt(ctx=ctx, game=current_game, guess=guess)
            return

        if not current_game and not guess:
            await self._start_game(ctx)


    @commands.command(name='stinks', help='Get a another image')
    async def stinks(self, ctx):
        current_game = self._get_game_in_progress(ctx.guild.id)

        if current_game:
            if current_game.clue_count >= MAX_CLUES:
                await ctx.channel.send(f'No more enough clues I\'m afraid mate')
                return

            rem_secs = current_game.time_remaining()
            if rem_secs > ALLOWED_CLUE_TIME:
                await ctx.channel.send(f'It\'s too early for a clue mate, try again in {int(rem_secs) - ALLOWED_CLUE_TIME} seconds')
                return

            await self._get_clue(ctx, current_game)
            return

        if not current_game:
            await ctx.channel.send('Can\'t get a clue when there\' no game to guess on mate')
            return


    @commands.command(name='sniffers', help='Get the Geo Sniff leaderboard')
    async def leaderboard(self, ctx):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{self.geo_score_api_url}/leaderboard', headers=HEADERS)
            leaderboard = resp.json()

            table = Texttable()
            table.set_deco(Texttable.HEADER)
            table.set_cols_dtype(['t', 'i', 'i', 'i'])
            table.set_cols_align(["l", "r", "r", "r"])

            table_rows = [["Name", "Played", "Won", "Points"]]

            for row in leaderboard:
                table_rows.append([value for (key, value) in row.items() if key != 'discordId'])

            table.add_rows(table_rows)

            await ctx.channel.send(f'```{table.draw()}```')






