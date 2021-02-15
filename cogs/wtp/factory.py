import os
import json
import random

from os.path import dirname
from PIL import Image
from io import BytesIO
from utils.files import FileRepo


IMGS_DIR = 'poke_imgs'
SOUNDS_DIR = 'poke_sounds'
SILS_PATH = 'poke_sils'
RESOURCE_PATH = os.path.join(dirname(dirname(dirname(os.path.abspath(__file__)))), 'resources/wtp')
JSON_DATA_PATH = os.path.join(RESOURCE_PATH, 'wtp_names.json')
BG_IMG_PATH = os.path.join(RESOURCE_PATH, 'wtp_bg.png')
BLACK_COL = (0, 0, 0, 255)
WTP_IMG_OFFSET = (290, 275)


class WtpPokemon:
    def __init__(self, poke_number, poke_names, poke_img_path, sil_img_path, poke_sound_path):
        self.number = poke_number
        self.names = poke_names
        self.poke_img_path = poke_img_path
        self.sil_img_path = sil_img_path
        self.poke_sound_path = poke_sound_path


class WtpPokemonFactory:
    def __init__(self, wtp_path, wtp_bucket_path):
        print('WTP factory is loading Pokemon assets...')
        self.wtp_path = wtp_path
        self.poke_imgs = FileRepo(base_path=os.path.join(wtp_path, IMGS_DIR), bucket_path=f'{wtp_bucket_path}/{IMGS_DIR}')
        self.poke_sounds = FileRepo(base_path=os.path.join(wtp_path, SOUNDS_DIR), bucket_path=f'{wtp_bucket_path}/{SOUNDS_DIR}')
        self.poke_sils = FileRepo(base_path=os.path.join(wtp_path, SILS_PATH))

        with open(JSON_DATA_PATH) as f:
            self.poke_names = json.load(f)

        print('WTP factory loading complete')


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


    def generate_wtp_img_bytes(self, pokemon, is_sil):
        wtp_bg = Image.open(BG_IMG_PATH)
        img_path = pokemon.sil_img_path if is_sil else pokemon.poke_img_path
        img = Image.open(img_path)

        x, y = img.size
        wtp_bg.paste(img, (int(WTP_IMG_OFFSET[0] - (x * 0.5)), int(WTP_IMG_OFFSET[1] - (y * 0.5))), img)

        full_img_bytes = BytesIO()
        wtp_bg.save(full_img_bytes, format='png')
        full_img_bytes.seek(0)

        return full_img_bytes


    def random(self):
        poke_data = random.choice(self.poke_names)
        poke_number = str(poke_data['number'])
        poke_names = poke_data['names']
        poke_path = self.poke_imgs.find(poke_number)
        sil_path = self._create_wtp_sil(poke_number, poke_path.get_path())

        print(f'WTP selecting random pokemon... {poke_names} ')

        pokemon = WtpPokemon(
            poke_number=poke_number,
            poke_names=poke_names,
            poke_img_path=poke_path.get_path(),
            sil_img_path=sil_path.get_path(),
            poke_sound_path=self.poke_sounds.find(poke_number).get_path()
        )

        return pokemon