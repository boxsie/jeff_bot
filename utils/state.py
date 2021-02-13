import os
import random
import json

from typing import List
from google.cloud import storage

from utils.gcs_helpers import connect_to_bucket, download_file, upload_file

STATE_JSON_FILENAME = 'state.json'


class BotUser(object):
    def __init__(self, user_id: str, user_name: str, nick_name:str, entrance_filename:str=None):
        self.user_id = user_id
        self.user_name = user_name
        self.entrance_filename = entrance_filename

    def add_entrance(self, audio_filename):
        self.entrance_filename = audio_filename

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class BotState(object):
    def __init__(self, users: List[BotUser]):
        self.users = users

    @classmethod
    def from_json(cls, data):
        users = list(map(BotUser.from_json, data["users"]))
        return cls(users)


class StateManager():
    def __init__(self, state_path, bucket_path=None):
        self.state_path = state_path

        if bucket_path:
            self._connect_to_bucket(bucket_path)

            if not self.bucket:
                raise Exception('Unable to connect to GCS bucket')

            print(f'Downloading the latest state from {bucket_path}')
            download_file(
                bucket=self.bucket,
                bucket_path=self.bucket_dir,
                filename=STATE_JSON_FILENAME,
                output_path=self.state_path,
                overwrite=True
            )

        self.state = self._load_state()


    def _state_json_path(self):
        return os.path.join(self.state_path, STATE_JSON_FILENAME)


    def _connect_to_bucket(self, bucket_path):
        bucket_name, bucket_dir = os.path.split(bucket_path)
        self.bucket = connect_to_bucket(bucket_name)
        self.bucket_dir = bucket_dir


    def _load_state(self):
        full_path = self._state_json_path()

        print(f'Loading state data json from {full_path}')

        if not os.path.exists(full_path):
            print('State data not found - Creating empty state')
            return BotState([])

        with open(full_path) as json_file:
            state_json = json.load(json_file)
            print('State data loaded')
            return BotState.from_json(state_json)


    def save_state(self):
        full_path = self._state_json_path()

        print(f'Saving state data json from {full_path}')

        if not os.path.exists(self.state_path):
            os.makedirs(self.state_path)

        with open(full_path, 'w') as outfile:
            json.dump(self.state, outfile, default=lambda o: o.__dict__, indent=4, sort_keys=True)

        if self.bucket:
            upload_file(
                bucket=self.bucket,
                source_path=full_path,
                bucket_path=self.bucket_dir,
                filename=STATE_JSON_FILENAME
            )


    def add_user(self, user_id, user_name, nick_name):
        if any(u for u in self.state.users if u.user_id == user_id):
            print(f'User {user_name} already exists')
            return

        user = BotUser(user_id, user_name, nick_name)
        print(f'Adding new user {user_id}:{user_name}')

        self.state.users.append(user)
        self.save_state()


    def add_users(self, bot_users):
        for user in bot_users:
            if any(u for u in self.state.users if u.user_id == user.user_id):
                print(f'User {user.user_name} already exists')
                continue

            print(f'Adding new user {user.user_id}:{user.user_name}')
            self.state.users.append(user)

        self.save_state()


    def get_user(self, user_id):
        user = next((u for u in self.state.users if u.user_id == user_id), None)

        if user:
            return user
        else:
            print(f'User {user_id} cannot be found')
            return None