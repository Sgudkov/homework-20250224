import datetime
import functools
import hashlib
import unittest

import api  # предполагается, что api.py содержит метод method_handler
from store import Store


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)

        return wrapper

    return decorator


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = Store(test=False)

    def get_response(self, request):
        return api.method_handler(
            {"body": request, "headers": self.headers}, self.context, self.store
        )

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(
                (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode(
                    "utf-8"
                )
            ).hexdigest()
        else:
            msg = (
                    request.get("account", "") + request.get("login", "") + api.SALT
            ).encode("utf-8")
            request["token"] = hashlib.sha512(msg).hexdigest()

    def test_redis_connection(self):
        self.assertTrue(self.store.connected)


    @cases(
        [
            {"client_ids": [1], "date": "20.07.2017"},
            {"client_ids": [1, 2], "date": "20.07.2017"},
            {"client_ids": [1, 2, 3], "date": "20.07.2017"},
        ]
    )
    def test_invalid_interests_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, _ = self.get_response(request)
        self.assertFalse(len(response), 0)

    @cases(
        [
            {"client_ids": [1, 2, 3, 4, 5], "date": "19.07.2017"},
            {"client_ids": [1, 2, 3, 4, 5, 6], "date": "19.07.2017"},
        ]
    )
    def test_ok_interests_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))


if __name__ == "__main__":
    unittest.main()
