import unittest

from unittest.mock import MagicMock, patch
import json

from server import app, apiSet, apiBinarySet, sets
from database import Database

class TestFunctions(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    @patch('server.Database')
    def test_apiSet(self, mockDatabase):
        mock_db = mockDatabase.return_value
        mock_db_data = [("0013-1", "Test Set", 2020, "Test Category", "http://example.com/image.jpg", "brickid10", "10", "100", "brick_name", "http://example.com/brick.jpg")]
        mock_db.execute_and_fetch_all.return_value = mock_db_data
        mockDatabase.return_value = mock_db

        response = self.client.get('/api/set?id=0013-1')
        args, kwargs = mock_db.execute_and_fetch_all.call_args
        assert "SELECT" in args[0]
        assert "lego_set" in args[0]
        assert "0013-1" in args[1]

        data = json.loads(response.data)

        assert data['name'] == 'Test Set'
        assert data['year'] == 2020
        assert data['category'] == 'Test Category'
        assert data['preview_image_url'] == 'http://example.com/image.jpg'
        assert data['inventory'][0]['color_id'] == '10'
        assert data['inventory'][0]['brick_type_id'] == 'brickid10'
        assert data['inventory'][0]['preview_image_url'] == 'http://example.com/brick.jpg'
        assert data['inventory'][0]['name'] == 'brick_name'
        assert data['inventory'][0]['count'] == '100'

    def apiBinarySetTest(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def setsTest(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

if __name__ == '__main__':
    unittest.main()