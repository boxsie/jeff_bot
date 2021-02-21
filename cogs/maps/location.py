STREET_VIEW_API_URL = 'https://maps.googleapis.com/maps/api/streetview?size=640x640&location={0},{1}&fov=100&heading={2}&pitch=0&key={3}'
STREET_META_API_URL = 'https://maps.googleapis.com/maps/api/streetview/metadata?size=640x640&location={0},{1}&fov=100&heading={2}&pitch=0&key={3}'

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