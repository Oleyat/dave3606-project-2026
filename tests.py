import unittest
import json
from server import apiSet, apiBinarySet, sets
from database import Database

class TestFunctions(unittest.TestCase):

    def apiSetTest(self):
        self.assertEqual('foo'.upper(), 'FOO')

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