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

GAME_TIME = 90
GAME_NAME = 'geosniff'

HEADERS = {'Content-type':'application/json', 'Accept':'application/json'}

class GeoSniff(commands.Cog):
    def __init__(self, bot, geo_sniff_api_url, google_api_token):
        self.bot = bot
        self.geo_sniff_api_url = geo_sniff_api_url
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
                "gameName": GAME_NAME,
                "discordId": ctx.message.author.id,
                "correctAnswer": game.get_answer()
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
                "gameId": game.game_id,
                "discordId": ctx.message.author.id,
                "attempt": guess.lower()
            }))


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
            await ctx.channel.send('There is no game to guess on!')
            return

        if current_game and guess:
            await self._make_attempt(ctx=ctx, game=current_game, guess=guess)
            return

        if not current_game and not guess:
            await self._start_game(ctx)