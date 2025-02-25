import json
import logging
import os

from dotenv import load_dotenv
import redis


class SingletonStore(type):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonStore, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Store(metaclass=SingletonStore):
    load_dotenv()

    def __init__(self, test=True):
        self.autoconnect_count = 3
        self.r = redis.Redis(
            host='redis-16160.c241.us-east-1-4.ec2.redns.redis-cloud.com',
            port=16160,
            decode_responses=True,
            username="default",
            password=self.__get_pass(),
            socket_timeout=3
        )
        if test:
            self.connected = False
            return
        self.connected = self.__is_connect()

        if self.connected:
            print('Connected')
        else:
            print('Not connected')
            print('Try to run under VPN')

    def __is_connect(self) -> bool:

        try:
            print('Trying to connect to redis...')
            self.autoconnect_count -= 1
            c = self.r.ping()
        except Exception:
            return False if self.autoconnect_count == 0 else self.__is_connect()

        return c

    def __get_pass(self):
        redis_pass = os.getenv('REDIS_PASSWORD')
        if redis_pass:
            return redis_pass

    def get(self, key):
        return None if not self.connected else self.r.get(key)

    def set(self, key, value):
        return None if not self.connected else self.r.set(key, value)

    def cache_get(self, key):
        return self.get(key)

    def cache_set(self, key, score, param):
        if self.connected:
            self.r.set(key, score, ex=param)

    def set_test_interests(self, key, value):
        return self.r.set(key, value)


def main():
    store = Store(test=False)
    test_set1 = [1, 2, 3, 4, 5, 6]
    request1 = {
        "account": "horns&hoofs",
        "login": "h&f",
        "method": "clients_interests",
        "arguments": {"client_ids": [1, 2, 3, 4, 5, 6], "date": "20.07.2017"},
    }
    test_set2 = [1, 2, 3, 4, 5]
    request2 = {
        "account": "horns&hoofs",
        "login": "h&f",
        "method": "clients_interests",
        "arguments": {"client_ids": [1, 2, 3, 4, 5], "date": "20.07.2017"},
    }
    s1 = f'i:{test_set1}'
    s2 = f'i:{test_set2}'
    print(store.set(s1, json.dumps(test_set1)))
    print(store.set(s2, json.dumps(test_set2)))


if __name__ == "__main__":
    main()
