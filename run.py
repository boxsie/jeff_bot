#!/usr/bin/env python3

import os
import argparse
import asyncio
import logging

from bot.client import BotClient
from utils.files import FileRepo
from utils.users import UserManager
from cogs.sound_board import SoundBoard
from cogs.entrances import Entrances
from cogs.google_img import GoogleImages
from cogs.wtp.whose_that_pokemon import WhoseThatPokemon
from cogs.maps.geo_sniff import GeoSniff
from commands.friday import friday


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser('''The Jeff Discord bot''')
    parser.add_argument('-discord_token', type=str, help='The discord token', required=True)
    parser.add_argument('-sounds_path', type=str, help='The sounds path', required=True)
    parser.add_argument('-user_api_url', type=str, help='The URL for the user store API', required=True)
    parser.add_argument('-wtp_path', type=str, help='The whose that pokemon media path', required=True)
    parser.add_argument('-gimg_api_token', type=str, help='The Google image search API token', required=True)
    parser.add_argument('-geo_sniff_api_url', type=str, help='The Geo Sniff api url', required=True)
    parser.add_argument('-gimg_api_cx', type=str, help='The Google image search API CX', required=True)
    parser.add_argument('-sounds_bucketpath', type=str, help='The sounds bucket path', default=None)
    parser.add_argument('-wtp_bucketpath', type=str, help='The whose that pokemon bucket path', default=None)
    parser.add_argument('-project_id', type=str, help='The GCP project ID', default=None)
    parser.add_argument('-bucket_sub_name', type=str, help='The project bucket pub/sub subscription name', default=None)
    args = parser.parse_args()
    print(f'Arguments processed: {args}')

    sound_files = FileRepo(args.sounds_path, args.sounds_bucketpath, args.project_id, args.bucket_sub_name)
    user_manager = UserManager(args.user_api_url)

    bot = BotClient(user_manager)
    bot.add_cog(SoundBoard(bot, sound_files))
    bot.add_cog(Entrances(bot, user_manager, sound_files))
    bot.add_cog(GoogleImages(bot, args.gimg_api_token, args.gimg_api_cx))
    bot.add_cog(WhoseThatPokemon(bot, args.wtp_path, args.wtp_bucketpath))
    bot.add_cog(GeoSniff(bot, args.geo_sniff_api_url, args.gimg_api_token))

    bot.add_command(friday)

    bot.run(args.discord_token)