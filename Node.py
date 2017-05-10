import os

def xor(s1, s2):
	return bytes(b1 ^ b2 for b1, b2 in zip(s1, s2))

def num_leading_zeros(bs):
	'''
	returns the number of leading 0 bits in byte string
	'''
	lz = 0
	for b in bs:
		for i in range(8):
			if (b >> (7 - i)) & 1:
				return lz
			lz += 1
	return lz

def bucket_index(distance):
	'''
	returns index j such that 2^j <= distance < 2^(j + 1)
	'''
	return 255 - num_leading_zeros(distance)

class Contact(object):
	def __init__(self, node_id, ip, port):
		self.node_id = node_id
		self.ip = ip
		self.port = port

	def __eq__(self, other):
		return self.node_id == other.node_id

	def __ne__(self, other):
		return not self.__eq__(other)


class Bucket(object):
	MAX_BUCKET_SIZE = 20
	def __init__(self):
		self.contacts = []

	def update(self, contact):
		#if contact exists, move it to end of bucket
		if contact in self.contacts:
			idx = self.contacts.index(contact)
			old = self.contacts.pop(idx)
			self.contacts.append(old)
		#if bucket not full, add contact to end
		elif len(self.contacts) < Bucket.MAX_BUCKET_SIZE:
			self.contacts.append(contact)
		#Otherwise, check if least recently contacted node is still
		#online. If not, evict it and add new contact
		else:
			#TODO: check if old node is online (for now just replace it)
			self.contacts.pop(0)
			self.append(contact)

class Node(object):
	def __init__(self):
		#node_id is randomly choosen
		self.node_id = os.urandom(32)
		self.buckets = [Bucket() for _ in range(256)]

	def distance(self, node_id):
		return xor(self.node_id, node_id)
	
	def update_route(self, contact):
		d = self.distance(contact.node_id)
		self.buckets[bucket_index(d)].update(contact)
