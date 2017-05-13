import binascii, os, socket, struct, sys

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

def bytes_to_hex(bs):
	return str(binascii.hexlify(bs), 'ascii')

class Contact(object):
	def __init__(self, node_id, ip, port):
		self.node_id = node_id
		self.ip = ip
		self.port = port

	def __eq__(self, other):
		return self.node_id == other.node_id

	def __ne__(self, other):
		return not self.__eq__(other)

	def encode(self):
		#TODO: how to handle IPv4 vs IPv6? (IPv4 to IPv6 mapping?)
		ip = socket.inet_aton(self.ip)
		port = struct.pack('!h', self.port)
		return b''.join([self.node_id, ip, port])

	@staticmethod
	def decode(raw):
		'''
		Takes binary representation of a Contact and decodes it returning new
		new Contact or None if representation is invalid
		'''
		if len(raw) != 32 + 4 + 2:
			return None
		node_id = raw[:32]
		ip = socket.inet_ntoa(raw[32:36])
		port = struct.unpack('!h', raw[36:40])[0]
		return Contact(node_id, ip, port)

	def __repr__(self):
		hs = bytes_to_hex(self.node_id)
		return 'Contact(addr=%s:%d, id=%s)' % (self.ip, self.port, hs)

class Bucket(object):
	MAX_BUCKET_SIZE = 20
	def __init__(self):
		#invariant: nodes are sorted by sorted by time since last contact
		#ie: least recently contacted is at head of list, more recently
		#contacted is at tail
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

	def empty(self):
		return len(self.contacts) == 0

	def __repr__(self):
		return 'Bucket([' + ',\n'.join([c.__repr__() for c in self.contacts]) + '])'

class Node(object):
	def __init__(self):
		#node_id is randomly chosen
		self.node_id = os.urandom(32)
		self.buckets = [Bucket() for _ in range(256)]

	def distance(self, node_id):
		'''
		returns the distance from the given node to this node
		the distance is the xor of the node ids
		this satisfies the properties:
		1) distance(x,x) = 0
		2) distance(x,y) = distance(y, x)
		3) distance(x,y) + distance(y, z) >= distance(x, z)
		'''
		return xor(self.node_id, node_id)

	def update_route(self, contact):
		'''
		takes a just contacted node and updates the routing tables
		'''
		d = self.distance(contact.node_id)
		self.buckets[bucket_index(d)].update(contact)

	def closest_nodes(self, node_id, k = 20):
		'''
		returns the k nodes in routing table closest to given node_id
		'''
		closest = []
		d = self.distance(node_id)
		idx = bucket_index(d)

		closest.extend(self.buckets[idx].contacts)

		i = 1
		#add nodes until we have >= k (or there are no more nodes left to add)
		while len(closest) < k and (idx - i >= 0 or idx + i < len(self.buckets)):
			if idx - i >= 0:
				closest.extend(self.buckets[idx - i].contacts)
			if idx + i < len(self.buckets):
				closest.extend(self.buckets[idx + i].contacts)
			i = i + 1
		#sort to get k closest
		#TODO: could be faster (computes xor too often)
		closest.sort(key=lambda c: xor(c.node_id, node_id))
		return closest[:k]

	def __repr__(self):
		hs = bytes_to_hex(self.node_id)
		bs = ',\n'.join([b.__repr__() for b in self.buckets if not b.empty()])
		return 'Node(id=%s, buckets=[%s])' % (hs, bs)

def port_str_valid(ps):
	if not ps.isdigit():
		return False
	port = int(ps)
	return port > 0 and port <= 65535
