import os
import discord
import sys

from io import BytesIO
from PIL import Image

from discord.ext import commands
from utils.files import FileRepo
from os.path import dirname

IMGS_DIR = 'poke_imgs'
SOUNDS_DIR = 'poke_sounds'
SILS_PATH = 'poke_sils'
BG_IMG_PATH = os.path.join(dirname(dirname(os.path.abspath(__file__))), 'resources/wtp/wtp_bg.png')
BLACK_COL = (0, 0, 0, 255)


class WhoseThatPokemon(commands.Cog):
    def __init__(self, bot, wtp_path, wtp_bucket_path):
        self.bot = bot
        self.wtp_path = wtp_path
        self.poke_imgs = FileRepo(base_path=os.path.join(wtp_path, IMGS_DIR), bucket_path=f'{wtp_bucket_path}/{IMGS_DIR}')
        self.poke_sounds = FileRepo(base_path=os.path.join(wtp_path, SOUNDS_DIR), bucket_path=f'{wtp_bucket_path}/{SOUNDS_DIR}')
        self.poke_sils = FileRepo(base_path=os.path.join(wtp_path, SILS_PATH))


    @commands.command(name='wtp', help='Start a round of whose that pokemon!')
    async def start_wtp(self, ctx):
        print(f'Starting whose that Pokemon.....')
        img_obj = self.poke_imgs.random()
        sil_obj = self.poke_sils.find(img_obj.name)
        poke_img = Image.open(img_obj.get_path())

        if not sil_obj:
            print('Pokemon silhouette not found creating new one...')
            width, height = poke_img.size

            for x in range(width):
                for y in range(height):
                    current_color = poke_img.getpixel((x, y))

                    if current_color[3] > 0:
                        poke_img.putpixel((x, y), BLACK_COL)

            filename = f'{img_obj.name}.png'
            full_path = os.path.join(self.wtp_path, SILS_PATH, filename)
            poke_img.save(full_path)
            sil_obj = self.poke_sils.add_file(filename)
            print(f'Silhouette {full_path} created!')

        wtp_bg_poke = Image.open(BG_IMG_PATH)
        wtp_bg_sil = Image.open(BG_IMG_PATH)

        file_path = sil_obj.get_path()
        sil_img = Image.open(file_path)

        x, y = sil_img.size
        wtp_bg_sil.paste(sil_img, (int(290 - (x * 0.5)), int(270 - (y * 0.5))), sil_img)
        wtp_bg_poke.paste(poke_img)

        full_img_bytes = BytesIO()
        wtp_bg_sil.save(full_img_bytes, format='png')
        full_img_bytes.seek(0)

        await ctx.channel.send(file=discord.File(full_img_bytes, 'whose-that-pokemon.png'))
