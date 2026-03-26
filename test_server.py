import unittest
from unittest import result
from unittest.mock import MagicMock, patch
import json
import gzip
from server import app, apiSet, apiBinarySet, sets
from database import Database
import struct
from binary_api import retLen, retData, readData, readDataRaw

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
        assert data['inventory'][0]['brick_name'] == 'brick_name'
        assert data['inventory'][0]['count'] == '100'


    @patch('server.Database')
    def test_Sets(self, mockDatabase):
        mock_db = mockDatabase.return_value
        
        mock_sets_data = [
            ("0013-1", "Test Set", 2020, "Category", "http://img.jpg"),
            ("0014-1", "Extra Set", 2021, "Category", "http://img.jpg") # fake data
        ]
        
        mock_db.execute_and_fetch_all.return_value = mock_sets_data
        response = self.client.get('/sets') 
        args, kwargs = mock_db.execute_and_fetch_all.call_args
        
        self.assertEqual(args[1], (51,)) 

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Encoding"], "gzip")
        html = gzip.decompress(response.data).decode('utf-8')
        self.assertIn("Test Set", html)
        self.assertIn("2020", html)
        self.assertIn("Category", html)
        self.assertIn("http://img.jpg", html)
        self.assertIn("Extra Set", html)
        self.assertIn("2021", html)
        self.assertIn("Category", html)
        self.assertIn("http://img.jpg", html)

    @patch('server.Database')
    def test_apiBinarySet(self, mockDatabase):
        mock_db = mockDatabase.return_value
        mock_db_data = [(
            "71799-1", "Market", "2023", "Ninjago", "http://img.com/s.png",
            "3001", "88", 2, "Brick", "http://img.com/P/88/1234.jpg"
        )]
        mock_db.execute_and_fetch_all.return_value = mock_db_data

        response = self.client.get('/api/binary/set?id=71799-1')
        self.assertEqual(response.status_code, 200)
        data = response.data
        offset = 0

        set_id_len = data[offset]
        offset += 1
        set_id = data[offset:offset+set_id_len].decode('utf-8')
        self.assertEqual(set_id, "71799-1")
        offset += set_id_len

        name_len = data[offset]
        offset += 1
        name = data[offset:offset+name_len].decode('utf-8')
        self.assertEqual(name, "Market")
        offset += name_len

        year = struct.unpack(">H", data[offset:offset+2])[0]
        self.assertEqual(year, 2023)
        offset += 2

        cat_len = data[offset]
        offset += 1
        cat = data[offset:offset+cat_len].decode('utf-8')
        self.assertEqual(cat, "Ninjago")
        offset += cat_len

        img_len = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        img_url = data[offset:offset+img_len].decode('utf-8')
        self.assertEqual(img_url, "http://img.com/s.png")
        offset += img_len

        self.assertEqual(data[offset], 88)
        offset += 1

        self.assertEqual(data[offset], 2)
        offset += 1

        type_flag = data[offset]
        self.assertEqual(type_flag, 104)
        offset += 1
        brick_type_val = struct.unpack(">H", data[offset:offset+2])[0]
        self.assertEqual(brick_type_val, 3001)
        offset += 2

        img_flag = data[offset]
        self.assertEqual(img_flag, 101)
        offset += 1
        img_val = struct.unpack(">H", data[offset:offset+2])[0]
        self.assertEqual(img_val, 1234)
        offset += 2

        bname_len = data[offset]
        offset += 1
        bname = data[offset:offset+bname_len].decode('utf-8')
        self.assertEqual(bname, "Brick")
        
if __name__ == '__main__':
    unittest.main()