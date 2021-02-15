import os
import httpx
import math
import discord
import asyncio
import numpy as np
import pandas as pd

from io import BytesIO
from PIL import Image
from zipfile import ZipFile
from os.path import dirname
from datetime import datetime

from discord.ext import commands


RESOURCE_PATH = os.path.join(dirname(dirname(dirname(os.path.abspath(__file__)))), 'resources/geo_sniff')
DATA_ZIP = os.path.join(RESOURCE_PATH, 'city_lats_longs.zip')
LATS_LONGS_CSV = 'city_lats_longs.csv'

STREET_VIEW_API_URL = 'https://maps.googleapis.com/maps/api/streetview?size=640x640&location={0},{1}&fov=100&heading={2}&pitch=0&key={3}'
STREET_META_API_URL = 'https://maps.googleapis.com/maps/api/streetview/metadata?size=640x640&location={0},{1}&fov=100&heading={2}&pitch=0&key={3}'
REV_GEO_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'

IMG_BORDER = 10
IMG_WIDTH = 640
IMG_HEIGHT = 640

GAME_TIME = 120


class Location(object):
    def __init__(self, lat, lng, heading=0):
        self.lat = lat
        self.lng = lng
        self.heading = heading


    def add_name_data(self, country=None, area=None, sub_area=None):
        self.country = country
        self.area = area
        self.sub_area = sub_area


    def street_view_img_url(self, api_key):
        return STREET_VIEW_API_URL.format(self.lat, self.lng, self.heading, api_key)


    def street_view_meta_url(self, api_key):
        return STREET_META_API_URL.format(self.lat, self.lng, self.heading, api_key)


    def to_string(self):
        return f'({self.lat}, {self.lng})'


    def to_filename(self):
        return f'{self.lat}-{self.lng}-{self.heading}'


class GeoSniffGame:
    def __init__(self, guild_id, location, on_complete, channel, loop):
        self.guild_id = guild_id
        self.location = location
        self.on_complete = on_complete
        self.channel = channel
        self.started_on = datetime.now().utcnow()
        self.game_timer = loop.create_task(self.time_out())
        self.finished = False


    async def time_out(self):
        await asyncio.sleep(GAME_TIME)

        self.finished = True
        await self.on_complete(self)


    def finish(self):
        self.finished = True

        if not self.game_timer.cancelled():
             self.game_timer.cancel()


    def make_attempt(self, user_id, guess):
        if not self.finished:
            if guess == self.location.sub_area.lower() or guess == self.location.area.lower() or guess == self.location.country.lower():
                self.finish()
                return True

        return False


class GeoSniff(commands.Cog):
    def __init__(self, bot, geo_sniff_path, api_token):
        self.bot = bot
        self.geo_sniff_path = geo_sniff_path
        self.api_token = api_token
        self.current_games = []

        print('Loading Geo Sniff data...')
        if not os.path.exists(self.geo_sniff_path):
            os.makedirs(self.geo_sniff_path)

            print('Unpacking CSV...')
            with ZipFile(DATA_ZIP, 'r') as zip_ref:
                zip_ref.extractall(self.geo_sniff_path)

        self.city_df = pd.read_csv(os.path.join(self.geo_sniff_path, LATS_LONGS_CSV), index_col=None)
        print(self.city_df.head())
        print('Geo Sniff loading complete')


    async def _get_random_location(self):
        final_loc = None

        while not final_loc:
            city_row = self.city_df.sample(n=1)[['latitude', 'longitude', 'accuracy_radius']]

            city_loc = Location(city_row.iloc[0]['latitude'], city_row.iloc[0]['longitude'])
            loc_rad = city_row.iloc[0]['accuracy_radius']

            final_loc = await self._find_random_street_view_loc(starting_loc=city_loc, radius=loc_rad)

            if final_loc:
                return await self._reverse_lookup_location(final_loc)


    async def _find_random_street_view_loc(self, starting_loc, radius):
        attempts = 0
        r_earth = 6378

        while True:
            a = np.random.rand() * 2 * math.pi
            r = radius * math.sqrt(np.random.rand())
            rand_x = r * math.cos(a)
            rand_y = r * math.sin(a)
            new_latitude  = starting_loc.lat + (rand_x / r_earth) * (180 / math.pi)
            new_longitude = starting_loc.lng + (rand_y / r_earth) * (180 / math.pi) / math.cos(starting_loc.lat * math.pi / 180)

            loc = await self._check_for_street_view_img(Location(new_latitude, new_longitude))

            if loc:
                return loc

            attempts += 1

            if attempts % 200 == 0:
                radius = radius * 2

            if attempts > 1000:
                return None


    async def _check_for_street_view_img(self, location):
        url = location.street_view_meta_url(self.api_token)
        print(f'Attempting to get street view meta from {location.to_string()}')

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                resp_json = resp.json()

                if 'status' in resp_json and resp_json['status'].lower() == 'ok':
                    return Location(
                        lat=resp_json['location']['lat'],
                        lng=resp_json['location']['lng'],
                        heading=location.heading
                    )
        except:
            raise Exception(f'Unable to get street view metadata for {location.to_string()}')


    async def _get_street_view_img(self, location):
        url = location.street_view_img_url(self.api_token)
        print(f'Attempting to get street view image from {location.to_string()}')

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                return BytesIO(resp.content)
        except:
            raise Exception(f'Unable to get street view image for {location.to_string()}')


    async def _reverse_lookup_location(self, loc):
        async with httpx.AsyncClient() as client:
            resp = await client.get(REV_GEO_API_URL.format(loc.lat, loc.lng, self.api_token))
            resp_json = resp.json()

            address_comp = resp_json['results'][0]['address_components']
            area = next((a['long_name'] for a in address_comp if 'administrative_area_level_1' in a['types']), "None")
            sub_area = next((a['long_name'] for a in address_comp if 'political' in a['types']), "None")
            country = next((a['long_name'] for a in address_comp if 'country' in a['types']), "None")

            loc.add_name_data(
                country=country,
                area=area,
                sub_area=sub_area
            )

            return loc


    async def _create_img_grid(self, loc):
        w = (IMG_BORDER * 3) + (IMG_WIDTH * 2)
        h = (IMG_BORDER * 3) + (IMG_HEIGHT * 2)
        img = Image.new('RGB', (w, h), (255, 255, 255))

        for i in range(4):
            new_loc = loc
            new_loc.heading += 90 * i

            if new_loc.heading > 360:
                new_loc.heading = new_loc.heading - 360

            print(f'Getting image with heading {new_loc.heading}')

            img_bytes = await self._get_street_view_img(new_loc)
            map_img = Image.open(img_bytes)

            if i == 0:
                img.paste(map_img, (IMG_BORDER, IMG_BORDER))
            elif i == 1:
                img.paste(map_img, (IMG_WIDTH + (IMG_BORDER * 2), IMG_BORDER))
            elif i == 2:
                img.paste(map_img, (IMG_BORDER, IMG_HEIGHT + (IMG_BORDER * 2)))
            else:
                img.paste(map_img, (IMG_WIDTH + (IMG_BORDER * 2), IMG_HEIGHT + (IMG_BORDER * 2)))

        full_img_bytes = BytesIO()
        img.save(full_img_bytes, format='png')
        full_img_bytes.seek(0)

        return full_img_bytes


    def _get_game_in_progress(self, guild_id):
        return next((g for g in self.current_games if g.guild_id == guild_id), None)


    async def _start_game(self, ctx):
        print(f'Starting Geo Sniff.....')
        await ctx.send(f'Jeff is sniffing one out...')

        loc = await self._get_random_location()
        img_grid_bytes = await self._create_img_grid(loc)

        game = GeoSniffGame(
            guild_id=ctx.guild.id,
            location=loc,
            on_complete=self._finish_game,
            channel=ctx.channel,
            loop=self.bot.loop
        )

        self.current_games.append(game)

        print(f'Geo Sniff has arrived at {loc.sub_area}, {loc.area}, {loc.country}')

        await ctx.channel.send(
            content='**Where is Jeff?**',
            file=discord.File(img_grid_bytes, 'where-is-jeff.png')
        )


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


    async def _finish_game(self, game, winning_user=None):
        self.current_games.remove(game)

        if winning_user:
            await game.channel.send(f'**{winning_user}** is the very best!')

        await game.channel.send(f'Jeff was in **{game.location.sub_area}, {game.location.area}, {game.location.country}**')

        print(f'Geo Sniff game complete!')


    @commands.command(name='sniff', help='Start a round of Geo Sniff!')
    async def wtp(self, ctx, guess=None):
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