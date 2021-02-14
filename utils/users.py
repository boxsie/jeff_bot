import os
import random
import json
import requests

HEADERS = {'Content-type':'application/json', 'Accept':'application/json'}

class BotUser(object):
    def __init__(self, user_id: str, user_name: str, entrance_filename:str=None):
        self.user_id = user_id
        self.user_name = user_name
        self.entrance_filename = entrance_filename

    def add_entrance(self, entrance_filename):
        self.entrance_filename = entrance_filename


class UserManager():
    def __init__(self, user_api_url):
        self.user_api_url = user_api_url
        self._load_users()


    def _load_users(self):
        response = requests.get(self.user_api_url, headers=HEADERS)
        users_json = response.json()
        self.users = [BotUser(user_id=u['discordId'], user_name=u['name'], entrance_filename=u['entranceSound']) for u in users_json]


    def _create_request(self, user):
        return {
            'name': user.user_name,
            'discordId': user.user_id,
            'entranceSound': user.entrance_filename
        }


    def add_user(self, user_id, user_name):
        req = self._create_request(BotUser(user_id=user_id, user_name=user_name))
        requests.post(self.user_api_url, data=json.dumps(req), headers=HEADERS)
        self._load_users()


    def add_users(self, bot_users):
        for user in bot_users:
            req = self._create_request(user)
            requests.post(self.user_api_url, data=json.dumps(req), headers=HEADERS)
        self._load_users()


    def add_entrance(self, user_id, entrance_sound):
        user = self.get_user(user_id)

        if not user:
            return

        user.add_entrance(entrance_sound)
        self.update_user(user)


    def get_user(self, user_id):
        response = requests.get(f'{self.user_api_url}/{user_id}', headers=HEADERS)

        if response.status_code != 404 and response.status_code != 400:
            response_json = response.json()

            return BotUser(
                 user_id=response_json['discordId'],
                 user_name=response_json['name'],
                 entrance_filename=response_json['entranceSound']
            )
        else:
            print(f'User {user_id} cannot be found')
            return None


    def update_user(self, user):
        req = self._create_request(user)
        response = requests.put(self.user_api_url, data=json.dumps(req), headers=HEADERS)
        self._load_users()