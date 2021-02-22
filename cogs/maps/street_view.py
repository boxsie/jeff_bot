import math
import httpx
import numpy as np

from io import BytesIO
from PIL import Image

from cogs.maps.location import Location

IMG_BORDER = 10
IMG_WIDTH = 640
IMG_HEIGHT = 640
RADIUS_ATTEMPTS = 50
RADIUS_GROW_CNT = 5
RADIUS_MULTI = 3
REV_GEO_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'


class StreetView:
    def __init__(self, geo_sniff_api_url, google_api_token):
        self.api_token = google_api_token
        self.geo_sniff_api_url = geo_sniff_api_url


    async def get_random_location(self):
        final_loc = None

        async with httpx.AsyncClient() as client:
            while not final_loc:
                resp = await client.get(self.geo_sniff_api_url)
                resp_json = resp.json()

                city_loc = Location(resp_json['lat'], resp_json['long'])
                loc_rad = resp_json['radius']

                final_loc = await self.find_random_street_view_loc(starting_loc=city_loc, radius=loc_rad)

                if final_loc:
                    return await self.reverse_lookup_location(final_loc)


    async def find_random_street_view_loc(self, starting_loc, radius):
        attempts = 0
        r_earth = 6378

        print(f'Attempting to get street view meta near {starting_loc.to_string()}')

        while True:
            a = np.random.rand() * 2 * math.pi
            r = radius * math.sqrt(np.random.rand())
            rand_x = r * math.cos(a)
            rand_y = r * math.sin(a)
            new_latitude  = starting_loc.lat + (rand_x / r_earth) * (180 / math.pi)
            new_longitude = starting_loc.lng + (rand_y / r_earth) * (180 / math.pi) / math.cos(starting_loc.lat * math.pi / 180)

            loc = await self.check_for_street_view_img(Location(new_latitude, new_longitude))

            if loc:
                return loc

            attempts += 1

            if attempts % RADIUS_ATTEMPTS == 0:
                print('Unable to find suitible location, expanding radius...')
                radius = radius * RADIUS_MULTI

            if attempts > RADIUS_GROW_CNT * RADIUS_ATTEMPTS:
                print('Unable to find suitible location, changing starting location')
                return None


    async def check_for_street_view_img(self, location):
        url = location.street_view_meta_url(self.api_token)

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


    async def get_street_view_img(self, location):
        url = location.street_view_img_url(self.api_token)
        print(f'Attempting to get street view image from {location.to_string()}')

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                return BytesIO(resp.content)
        except:
            raise Exception(f'Unable to get street view image for {location.to_string()}')


    async def reverse_lookup_location(self, loc):
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


    async def create_img_grid(self, loc):
        w = (IMG_BORDER * 3) + (IMG_WIDTH * 2)
        h = (IMG_BORDER * 3) + (IMG_HEIGHT * 2)
        img = Image.new('RGB', (w, h), (255, 255, 255))

        for i in range(4):
            new_loc = loc
            new_loc.heading += 90 * i

            if new_loc.heading > 360:
                new_loc.heading = new_loc.heading - 360

            print(f'Getting image with heading {new_loc.heading}')

            img_bytes = await self.get_street_view_img(new_loc)
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