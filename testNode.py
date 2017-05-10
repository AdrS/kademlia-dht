import unittest
from Node import *

class TestHelpers(unittest.TestCase):
	def test_xor(self):
		self.assertEqual(xor(b'\x01'*5, b'\x02'*5), b'\x03'*5)

	def test_num_leading_zeros(self):
		self.assertEqual(num_leading_zeros(b'\x00'), 8)
		self.assertEqual(num_leading_zeros(b'\x10..'), 3)
		self.assertEqual(num_leading_zeros(b'\x80..'), 0)
		self.assertEqual(num_leading_zeros(b'\x00\x00\x04..'), 21)

	def test_bucket_index(self):
		self.assertEqual(bucket_index(b'\x00'*31 + b'\x01'), 0)
		self.assertEqual(bucket_index(b'\x00'*31 + b'\x02'), 1)
		self.assertEqual(bucket_index(b'\x00'*31 + b'\x03'), 1)
		self.assertEqual(bucket_index(b'\x00'*31 + b'\x07'), 2)
		self.assertEqual(bucket_index(b'\xff'*32), 255)

class TestContact(unittest.TestCase):
	def test_eq(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		c2 = Contact(b'\x01'*32, '123.21.12.231', 1235)
		c3 = Contact(b'\x02'*32, '123.21.12.231', 1235)

		self.assertEqual(c1, c1)
		self.assertEqual(c1, c2)
		self.assertFalse(c1 == c3)
		self.assertFalse(c2 == c3)

	def test_ne(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		c2 = Contact(b'\x01'*32, '123.21.12.231', 1235)
		c3 = Contact(b'\x02'*32, '123.21.12.231', 1235)

		self.assertFalse(c1 != c1)
		self.assertFalse(c1 != c2)
		self.assertNotEqual(c1, c3)
		self.assertNotEqual(c2, c3)

class TestBucket(unittest.TestCase):
	def test_init(self):
		b = Bucket()
		self.assertTrue(len(b.contacts) == 0)
	
	def test_update(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		c1p = Contact(b'\x01'*32, '123.21.12.231', 1235)
		c2 = Contact(b'\x02'*32, '123.21.12.231', 1235)
		c3 = Contact(b'\x03'*32, '123.21.12.231', 1235)

		b = Bucket()
		#test on empty bucket
		b.update(c1)
		self.assertEqual(b.contacts, [c1])

		#update should not do anything if contact already there
		b.update(c1)
		self.assertEqual(b.contacts, [c1])

		#update should give preference to origional contact with given id
		b.update(c1p)
		self.assertEqual(b.contacts, [c1])
		self.assertEqual(b.contacts[0].port, c1.port)

		#add new contact when there is space left
		b.update(c2)
		self.assertEqual(b.contacts, [c1, c2])
		b.update(c3)
		self.assertEqual(b.contacts, [c1, c2, c3])

		b.update(c2)
		self.assertEqual(b.contacts, [c1, c3, c2])

		#TODO: add tests for full contact list
		#note: eviction depends on network activity, so test more complicated

		
if __name__ == '__main__':
	unittest.main()
