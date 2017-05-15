import unittest
from KeyValueStore import *

class TestValue(unittest.TestCase):
	def test_expired(self):
		v = Value('hi')
		self.assertFalse(v.expired())

		v = Value('hi', time.time() + 5)
		self.assertFalse(v.expired())

		v = Value('bye', time.time() - 5)
		self.assertTrue(v.expired())

class TestKeyValueStore(unittest.TestCase):
	def test(self):
		s = KeyValueStore()
		s.set('hi', 1, -1)
		self.assertEqual(s['hi'], 1)
		self.assertTrue('hi' in s)
		s['hi'] = 2
		self.assertEqual(s['hi'], 2)

	def test_remove_expired(self):
		s = KeyValueStore(1)
		s['a'] = 1
		s['b'] = 2
		s['c'] = 3
		s.set('d', 4, 3)
		s.set('e', 5, -1)
		self.assertTrue('a' in s)
		self.assertTrue('b' in s)
		self.assertTrue('c' in s)
		self.assertTrue('d' in s)
		self.assertTrue('e' in s)
		self.assertEqual(s['a'], 1)
		self.assertEqual(s['b'], 2)
		self.assertEqual(s['c'], 3)
		self.assertEqual(s['d'], 4)
		self.assertEqual(s['e'], 5)

		time.sleep(1.1)
		s.remove_expired()
		self.assertFalse('a' in s)
		self.assertFalse('b' in s)
		self.assertFalse('c' in s)
		self.assertTrue('d' in s)
		self.assertTrue('e' in s)
		time.sleep(2.1)
		s.remove_expired()
		self.assertFalse('a' in s)
		self.assertFalse('b' in s)
		self.assertFalse('c' in s)
		self.assertFalse('d' in s)
		self.assertTrue('e' in s)


if __name__ == '__main__':
	unittest.main()
