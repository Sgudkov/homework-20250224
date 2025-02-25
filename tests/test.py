import unittest

import api  # предполагается, что api.py содержит метод method_handler


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = None

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    def test_empty_request(self):
        response, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)


if __name__ == "__main__":
    unittest.main()
