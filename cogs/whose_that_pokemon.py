import os
import discord
import sys
import json
import random
import asyncio

from datetime import datetime
from io import BytesIO
from PIL import Image

from discord.ext import commands
from utils.files import FileRepo
from os.path import dirname
from utils.discord_helpers import get_channel_from_ctx

IMGS_DIR = 'poke_imgs'
SOUNDS_DIR = 'poke_sounds'
SILS_PATH = 'poke_sils'
RESOURCE_PATH = os.path.join(dirname(dirname(os.path.abspath(__file__))), 'resources/wtp')
BG_IMG_PATH = os.path.join(RESOURCE_PATH, 'wtp_bg.png')
JSON_DATA_PATH = os.path.join(RESOURCE_PATH, 'wtp_names.json')
BLACK_COL = (0, 0, 0, 255)
WTP_IMG_OFFSET = (290, 275)
GAME_TIME = 30


class WtpPokemonFactory:
    def __init__(self, wtp_path, wtp_bucket_path):
        self.wtp_path = wtp_path
        self.poke_imgs = FileRepo(base_path=os.path.join(wtp_path, IMGS_DIR), bucket_path=f'{wtp_bucket_path}/{IMGS_DIR}')
        self.poke_sounds = FileRepo(base_path=os.path.join(wtp_path, SOUNDS_DIR), bucket_path=f'{wtp_bucket_path}/{SOUNDS_DIR}')
        self.poke_sils = FileRepo(base_path=os.path.join(wtp_path, SILS_PATH))

        with open(JSON_DATA_PATH) as f:
            self.poke_names = json.load(f)


    def _create_wtp_sil(self, poke_number, poke_img_path):
        poke_img = Image.open(poke_img_path)
        sil_obj = self.poke_sils.find(poke_number)

        if sil_obj:
            return sil_obj

        print('Pokemon silhouette not found creating new one...')
        width, height = poke_img.size

        for x in range(width):
            for y in range(height):
                current_color = poke_img.getpixel((x, y))

                if current_color[3] > 0:
                    poke_img.putpixel((x, y), BLACK_COL)

        filename = f'{poke_number}.png'
        full_path = os.path.join(self.wtp_path, SILS_PATH, filename)
        poke_img.save(full_path)
        sil_obj = self.poke_sils.add_file(filename)
        print(f'Silhouette {full_path} created!')

        return sil_obj


    def random(self):
        poke_data = random.choice(self.poke_names)
        poke_number = str(poke_data['number'])
        poke_names = poke_data['names']
        poke_path = self.poke_imgs.find(poke_number)
        sil_path = self._create_wtp_sil(poke_number, poke_path.get_path())

        pokemon = WtpPokemon(
            poke_number=poke_number,
            poke_names=poke_names,
            poke_img=Image.open(poke_path.get_path()),
            sil_img=Image.open(sil_path.get_path()),
            poke_sound_path=self.poke_sounds.find(poke_number).get_path()
        )

        return pokemon


class WtpPokemon:
    def __init__(self, poke_number, poke_names, poke_img, sil_img, poke_sound_path):
        self.number = poke_number
        self.names = poke_names
        self.poke_img = poke_img
        self.sil_img = sil_img
        self.poke_sound_path = poke_sound_path


    def get_poke_img_bytes(self):
        return self._paste_pokemon_to_bg(self.poke_img)


    def get_sil_img_bytes(self):
        return self._paste_pokemon_to_bg(self.sil_img)


    def _paste_pokemon_to_bg(self, poke_img):
        wtp_bg = Image.open(BG_IMG_PATH)
        x, y = poke_img.size

        wtp_bg.paste(poke_img, (int(WTP_IMG_OFFSET[0] - (x * 0.5)), int(WTP_IMG_OFFSET[1] - (y * 0.5))), poke_img)

        full_img_bytes = BytesIO()
        wtp_bg.save(full_img_bytes, format='png')
        full_img_bytes.seek(0)

        return full_img_bytes


class WtpGame:
    def __init__(self, guild_id, pokemon, on_complete):
        self.guild_id = guild_id
        self.pokemon = pokemon
        self.on_complete = on_complete
        self.attempts = []


    def start(self, channel, loop):
        self.channel = channel
        self.started_on = datetime.now().utcnow()
        self.game_timer = loop.create_task(self.time_out())


    async def time_out(self):
        await asyncio.sleep(GAME_TIME)
        await self.on_complete(self)


    def finish(self):
        if not self.game_timer.cancelled():
             self.game_timer.cancel()


    def make_attempt(self, user_id, guess):
        self.attempts.append({
            'user_id': user_id,
            'guess': guess,
            'attempt_time': datetime.now().utcnow()
        })

        return any(guess == n for n in list(self.pokemon.names.values()))


class WhoseThatPokemon(commands.Cog):
    def __init__(self, bot, wtp_path, wtp_bucket_path):
        self.bot = bot
        self.poke_factory = WtpPokemonFactory(
            wtp_path=wtp_path,
            wtp_bucket_path=wtp_bucket_path
        )
        self.current_games = []


    def _get_game_in_progress(self, guild_id):
        return next((g for g in self.current_games if g.guild_id == guild_id), None)


    async def _start_wtp_game(self, guild_id, channel, on_complete):
        print(f'Starting whose that Pokemon.....')

        game = WtpGame(
            guild_id=guild_id,
            pokemon=self.poke_factory.random(),
            on_complete=on_complete
        )

        game.start(channel=channel, loop=self.bot.loop)

        return game


    async def _finish_wtp_game(self, wtp_game):
        name_en = wtp_game.pokemon.names['en']
        await wtp_game.channel.send(content=f'It was **{name_en.capitalize()}**', file=discord.File(wtp_game.pokemon.get_poke_img_bytes(), f'{name_en}.png'))
        wtp_game.finish()
        self.current_games.remove(wtp_game)
        print(f'Whose that Pokemon game complete!')


    @commands.command(name='wtp', help='Start a round of whose that pokemon!')
    async def start_wtp(self, ctx, guess=None):
        current_game = self._get_game_in_progress(ctx.guild.id)

        if not current_game:
            if guess:
                await ctx.channel.send('There is no game in progress to guess on!')
            else:
                game = await self._start_wtp_game(
                    guild_id=ctx.guild.id,
                    channel=ctx.channel,
                    on_complete=self._finish_wtp_game
                )

                print(game.pokemon.names)
                self.current_games.append(game)
                channel = get_channel_from_ctx(bot=self.bot, ctx=ctx)
                await self.bot.voice.play(channel=channel, source=game.pokemon.poke_sound_path, title='Whose that pokemon?')
                await ctx.channel.send(file=discord.File(game.pokemon.get_sil_img_bytes(), 'whose-that-pokemon.png'))
                await ctx.channel.send(f'*you have {GAME_TIME} seconds to answer - type !wtp "POKEMON NAME" to play*')
        else:
            if guess:
                result = current_game.make_attempt(
                    user_id=ctx.message.author.id,
                    guess=guess.lower()
                )

                if result:
                    await ctx.channel.send(f'{ctx.message.author.name} is the very best!')
                    await self._finish_wtp_game(current_game)
                else:
                    await ctx.message.add_reaction('\N{THUMBS DOWN SIGN}')
            else:
                await ctx.channel.send('There is already a game in process!')
