#!/usr/bin/env python3

import os
import argparse
import asyncio
import logging
import json

from bot.client import BotClient
from utils.files import FileRepo
from utils.users import UserManager
from utils.config import Config
from cogs.sound_board import SoundBoard
from cogs.entrances import Entrances
from cogs.google_img import GoogleImages
from cogs.wtp.whose_that_pokemon import WhoseThatPokemon
from cogs.maps.geo_sniff import GeoSniff
from commands.friday import friday

CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')

def _load_json_config(base_bucket, base_api):
    with open(CONFIG_FILE) as json_file:
        return Config(
            cfg_json=json.load(json_file),
            base_bucket=base_bucket,
            base_api=base_api
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser('''The Jeff Discord bot''')
    parser.add_argument('-discord_token', type=str, help='The discord token', required=True)
    parser.add_argument('-gimg_api_cx', type=str, help='The Google image search API CX', required=True)
    parser.add_argument('-gimg_api_token', type=str, help='The Google image search API token', required=True)
    parser.add_argument('-project_id', type=str, help='The GCP project ID', default=None)
    parser.add_argument('-bucket_sub_name', type=str, help='The project bucket pub/sub subscription name', default=None)
    parser.add_argument('-api_url', type=str, help='The base API url', required=True)
    parser.add_argument('-bucket_path', type=str, help='The base bucket path', required=True)
    args = parser.parse_args()
    print(f'Arguments processed: {args}')

    config = _load_json_config(
        base_bucket=args.bucket_path,
        base_api=args.api_url
    )

    sound_files = FileRepo(
        base_path=config.paths['sounds'],
        bucket_path=config.get_bucket_path('sounds'),
        project_id=args.project_id,
        bucket_sub_name=args.bucket_sub_name
    )

    user_manager = UserManager(
        user_api_url=config.get_api_url('user')
    )

    bot = BotClient(
        user_manager=user_manager
    )

    bot.add_cog(SoundBoard(
        bot=bot,
        sound_files=sound_files
    ))

    bot.add_cog(Entrances(
        bot=bot,
        user_manager=user_manager,
        sound_files=sound_files
    ))

    bot.add_cog(GoogleImages(
        bot=bot,
        api_token=args.gimg_api_token,
        api_cx=args.gimg_api_cx
    ))

    bot.add_cog(WhoseThatPokemon(
        bot=bot,
        wtp_path=config.paths['wtp'],
        wtp_bucket_path=config.get_bucket_path('wtp')
    ))

    bot.add_cog(GeoSniff(
        bot=bot,
        geo_sniff_api_url=config.get_api_url('geo_sniff'),
        geo_score_api_url=config.get_api_url('geo_score'),
        google_api_token=args.gimg_api_token
    ))

    bot.add_command(friday)

    bot.run(args.discord_token)