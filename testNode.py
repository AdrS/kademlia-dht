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

	def test_port_str_valid(self):
		self.assertTrue(port_str_valid('123'))
		self.assertTrue(port_str_valid('65535'))
		self.assertTrue(port_str_valid('8888'))
		#source: https://www.grc.com/port_0.htm
		self.assertFalse(port_str_valid('0'))
		self.assertFalse(port_str_valid('asfd'))
		self.assertFalse(port_str_valid('65536'))
		self.assertFalse(port_str_valid('-2134'))

	def test_insort_right(self):
		a = [('a',1), ('b',2), ('d', 4)]
		insort_right(a, ('c',3), lambda x,y: x[0] < y[0])
		self.assertEqual(a, [('a',1), ('b',2), ('c', 3), ('d', 4)])

		insort_right(a, ('z',0), lambda x,y: x[1] < y[1])
		self.assertEqual(a, [('z', 0), ('a',1), ('b',2), ('c', 3), ('d', 4)])

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

	def test_encode(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 0x1234)
		c2 = Contact(b'\x02'*32, '16.0.0.255', 0x34)
		self.assertEqual(c1.encode(), b'\x01'*32 + b'{\x15\x0c\xe7' + b'\x12\x34')
		self.assertEqual(c2.encode(), b'\x02'*32 + b'\x10\x00\x00\xff' + b'\x00\x34')

	def test_decode(self):
		self.assertEqual(Contact.decode(b'a'*12), None)

		c1 = Contact(b'\x01'*32, '123.21.12.231', 0xf234)
		c1p = Contact.decode(c1.encode())
		self.assertEqual(c1p.node_id, c1.node_id)
		self.assertEqual(c1p.ip, c1.ip)
		self.assertEqual(c1p.port, c1.port)

		c2 = Contact(b'\x02'*32, '16.0.0.255', 0x34)
		c2p = Contact.decode(c2.encode())
		self.assertEqual(c2p.node_id, c2.node_id)
		self.assertEqual(c2p.ip, c2.ip)
		self.assertEqual(c2p.port, c2.port)

	def test_repr(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		self.assertEqual(c1.__repr__(), 'Contact(addr=123.21.12.231:1234, id=' + '01'*32 + ')')

	def test_update_last_seen(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		time.sleep(0.1)
		c1.update_last_seen()
		self.assertTrue((c1.last_seen - time.time()) < 0.001)

def el1s(l):
	return [i[0] for i in l]

class TestBucket(unittest.TestCase):
	def test_init(self):
		b = Bucket()
		self.assertTrue(len(b.contacts) == 0)

	def test_remove_expired(self):
		#should I just test update directly???
		#TODO: write update tests for situations where there
		#	are nodes pending removal
		pass

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
		#must do test for when contact is in pending addition or pending removal
		b = Bucket(3)
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		c1p = Contact(b'\x01'*32, '123.21.12.231', 1235)
		c2 = Contact(b'\x02'*32, '123.21.12.231', 1235)
		c3 = Contact(b'\x03'*32, '123.21.12.231', 1235)
		c4 = Contact(b'\x04'*32, '123.21.12.231', 1235)
		c5 = Contact(b'\x05'*32, '123.21.12.231', 1235)
		c6 = Contact(b'\x06'*32, '123.21.12.231', 1235)
		c7 = Contact(b'\x07'*32, '123.21.12.231', 1235)

		self.assertIsNone(b.update(c1))
		#space for previously unseen contact
		self.assertEqual(b.contacts, [c1])
		self.assertEqual(b.pending_removal, [])
		self.assertEqual(b.pending_addition, [])

		#contact already in list => not changes
		self.assertIsNone(b.update(c1))
		self.assertEqual(b.contacts, [c1])
		self.assertEqual(b.pending_removal, [])
		self.assertEqual(b.pending_addition, [])

		self.assertIsNone(b.update(c2))
		self.assertEqual(b.contacts, [c1, c2])
		self.assertEqual(b.pending_removal, [])
		self.assertEqual(b.pending_addition, [])

		self.assertIsNone(b.update(c3))
		self.assertEqual(b.contacts, [c1, c2, c3])
		self.assertEqual(b.pending_removal, [])
		self.assertEqual(b.pending_addition, [])

		self.assertIsNone(b.update(c2))
		#see contact => moves to back of list
		self.assertEqual(b.contacts, [c1, c3, c2])
		self.assertEqual(b.pending_removal, [])
		self.assertEqual(b.pending_addition, [])

		self.assertEqual(b.update(c4), c1)
		#contact list full => must remove one
		self.assertEqual(b.contacts, [c3, c2])
		self.assertEqual(len(b.pending_removal), 1)
		self.assertEqual(b.pending_removal[0][0], c1)
		e1 = time.time() + 10
		self.assertTrue(abs(b.pending_removal[0][1] - e1) < 0.01)
		self.assertEqual(b.pending_addition, [c4])

		self.assertIsNone(b.update(c3))
		#seeing existing contact should not change pending add/remove lists
		self.assertEqual(b.contacts, [c2, c3])
		self.assertEqual(len(b.pending_removal), 1)
		self.assertEqual(b.pending_removal[0][0], c1)
		self.assertTrue(abs(b.pending_removal[0][1] - e1) < 0.01)
		self.assertEqual(b.pending_addition, [c4])

		#seeing node that is pending removal should save it
		self.assertIsNone(b.update(c1))
		self.assertEqual(b.contacts, [c2, c3, c1])
		self.assertEqual(b.pending_removal, [])
		self.assertEqual(b.pending_addition, [])

		self.assertEqual(b.update(c4, 0.1), c2)
		self.assertEqual(b.update(c5, 0.1), c3)
		self.assertEqual(b.update(c6, 0.4), c1)
		self.assertEqual(b.contacts, [])
		self.assertEqual(el1s(b.pending_removal), [c2, c3, c1])
		self.assertEqual(b.pending_addition, [c4, c5, c6])

		#full set of contacts pending addition => ignore any new ones
		self.assertIsNone(b.update(c7))
		self.assertEqual(b.contacts, [])
		self.assertEqual(el1s(b.pending_removal), [c2, c3, c1])
		self.assertEqual(b.pending_addition, [c4, c5, c6])

		t1 = c4.last_seen

		#seeing pending addition updates last seen time
		self.assertIsNone(b.update(c4))
		self.assertEqual(b.contacts, [])
		self.assertEqual(el1s(b.pending_removal), [c2, c3, c1])
		self.assertEqual(b.pending_addition, [c4, c5, c6])
		self.assertTrue(t1 < c4.last_seen)

		#stale contacts should get removed
		time.sleep(0.2)
		self.assertEqual(b.update(c7), c5)
		self.assertEqual(el1s(b.pending_removal), [c1, c5])
		self.assertEqual(b.pending_addition, [c6, c7])
		self.assertEqual(b.contacts, [c4])

		time.sleep(0.2)
		self.assertIsNone(b.update(c4))
		self.assertEqual(el1s(b.pending_removal), [c5])
		self.assertEqual(b.pending_addition, [c7])
		self.assertEqual(b.contacts, [c6, c4])

class TestNode(unittest.TestCase):
	def test_update_route(self):
		#just wrapper for bucket update
		pass

	def test_closest_nodes(self):
		c1 = Contact(b'\x01'*32, '123.21.12.231', 1234)
		c2 = Contact(b'\x02'*32, '123.21.12.231', 1234)
		c3 = Contact(b'\x03'*32, '123.21.12.231', 1234)
		c4 = Contact(b'\x04'*32, '123.21.12.231', 1234)
		c5 = Contact(b'\x05'*32, '123.21.12.231', 1234)
		c6 = Contact(b'\x06'*32, '123.21.12.231', 1234)
		n = Node()
		for c in [c1, c2, c3, c4, c5, c6]:
			n.update_route(c)
		self.assertEqual(n.closest_nodes(b'\x02'*32, 10), [c2, c3, c1, c6, c4, c5])
		self.assertEqual(n.closest_nodes(b'\x02'*32, 1), [c2])
		self.assertEqual(n.closest_nodes(b'\x08'*32, 3), [c1, c2, c3])

if __name__ == '__main__':
	unittest.main()
