


class Config:
    def __init__(self, cfg_json, base_bucket, base_api):
        self.paths = cfg_json['path']
        self.api = cfg_json['api']
        self.base_bucket = base_bucket
        self.base_api = base_api


    def get_bucket_path(self, resource_name):
        if not resource_name in self.paths:
            raise Exception(f'Cannot find the resource path for {resource_name}')

        return f'{self.base_bucket}/{self.paths[resource_name]}'


    def get_api_url(self, api_name):
        if not api_name in self.api:
            raise Exception(f'Cannot find the api url for {api_name}')

        return f'{self.base_api}/{self.api[api_name]}'






