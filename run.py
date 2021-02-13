#!/usr/bin/env python3

import os
import argparse
import asyncio
import logging

from bot.client import BotClient
from utils.files import FileRepo
from utils.state import StateManager
from cogs.sound_board import SoundBoard
from cogs.entrances import Entrances
from cogs.google_img import GoogleImages
from cogs.whose_that_pokemon import WhoseThatPokemon
from commands.friday import friday


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser('''The Jeff Discord bot''')
    parser.add_argument('-discord_token', type=str, help='The discord token', required=True)
    parser.add_argument('-sounds_path', type=str, help='The sounds path', required=True)
    parser.add_argument('-state_path', type=str, help='The data path', required=True)
    parser.add_argument('-wtp_path', type=str, help='The whose that pokemon media path', required=True)
    parser.add_argument('-gimg_api_token', type=str, help='The Google image search API token', required=True)
    parser.add_argument('-gimg_api_cx', type=str, help='The Google image search API CX', required=True)
    parser.add_argument('-sounds_bucketpath', type=str, help='The sounds bucket path', default=None)
    parser.add_argument('-state_bucketpath', type=str, help='The data bucket path', default=None)
    parser.add_argument('-wtp_bucketpath', type=str, help='The whose that pokemon bucket path', default=None)
    parser.add_argument('-project_id', type=str, help='The GCP project ID', default=None)
    parser.add_argument('-bucket_sub_name', type=str, help='The project bucket pub/sub subscription name', default=None)
    args = parser.parse_args()
    print(f'Arguments processed: {args}')

    token = args.discord_token
    sounds_path = args.sounds_path
    sounds_bucket_path = args.sounds_bucketpath
    state_path = args.state_path
    state_bucket_path = args.state_bucketpath
    project_id = args.project_id
    bucket_sub_name = args.bucket_sub_name
    gimg_api_token = args.gimg_api_token
    gimg_api_cx = args.gimg_api_cx
    wtp_path = args.wtp_path
    wtp_bucket_path = args.wtp_bucketpath

    sound_files = FileRepo(sounds_path, sounds_bucket_path, project_id, bucket_sub_name)
    state_manager = StateManager(state_path, state_bucket_path)

    bot = BotClient(state_manager)
    bot.add_cog(SoundBoard(bot, sound_files))
    bot.add_cog(Entrances(bot, state_manager, sound_files))
    bot.add_cog(GoogleImages(bot, gimg_api_token, gimg_api_cx))
    bot.add_cog(WhoseThatPokemon(bot, wtp_path, wtp_bucket_path))

    bot.add_command(friday)

    bot.run(token)