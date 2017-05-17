import binascii, KeyValueStore, os, socket, struct, sys, time

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
		self.last_seen = time.time()

	def __eq__(self, other):
		return self.node_id == other.node_id

	def __ne__(self, other):
		return not self.__eq__(other)

	def encode(self):
		#TODO: how to handle IPv4 vs IPv6? (IPv4 to IPv6 mapping?)
		ip = socket.inet_aton(self.ip)
		port = struct.pack('!H', self.port)
		return b''.join([self.node_id, ip, port])

	def update_last_seen(self):
		self.last_seen = time.time()

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
		port = struct.unpack('!H', raw[36:40])[0]
		return Contact(node_id, ip, port)

	def __repr__(self):
		hs = bytes_to_hex(self.node_id)
		return 'Contact(addr=%s:%d, id=%s)' % (self.ip, self.port, hs)

def insort_right(a, x, lt):
	'''
	Like https://github.com/python/cpython/blob/3.6/Lib/bisect.py, but takes
	lambda for comparisions
	'''
	lo = 0
	hi = len(a)
	while lo < hi:
		mid = (lo + hi)//2
		if lt(x, a[mid]):
			hi = mid
		else:
			lo = mid + 1
	a.insert(lo, x)

class Bucket(object):
	def __init__(self, max_size=20):
		#invariant: nodes are sorted by sorted by time since last contact
		#ie: least recently contacted is at head of list, more recently
		#contacted is at tail
		self.contacts = []
		self.pending_removal = [] #(contact, expiration)
		self.pending_addition = []
		self.max_size = max_size

	def remove_expired(self):
		'''
		Removes expired contacts from pending_removal list and adds
		coresponding contants in pending_addition list to contacts
		'''
		npr = []
		npa = []
		for i, (c, e) in enumerate(self.pending_removal):
			if e > time.time():
				#not expired yet => keep
				npr.append((c,e))
				npa.append(self.pending_addition[i])
			else:
				#insert new contact maintaining invariant that contacts are
				#sorted by time last seen
				lt = lambda x, y: x.last_seen < y.last_seen
				insort_right(self.contacts, self.pending_addition[i], lt)
		self.pending_removal = npr
		self.pending_addition = npa

	def update(self, contact, ttl=10):
		'''
		Updates bucket. Returns lru contact for server to ping if there
		is not enough space for another node. CALLER must ping lru contact
		if such a contact is returned
		'''
		assert(len(self.contacts) + len(self.pending_removal) <= self.max_size)
		assert(len(self.pending_addition) == len(self.pending_removal))

		self.remove_expired()

		if contact in self.contacts:
			#if contact exists, move it to end of bucket
			idx = self.contacts.index(contact)
			old = self.contacts.pop(idx)
			old.update_last_seen()
			self.contacts.append(old)
		elif contact in self.pending_addition:
			#see contact pending addition => update last seen time
			idx = self.pending_addition.index(contact)
			self.pending_addition[idx].update_last_seen()
		else:
			pr = [i[0] for i in self.pending_removal]
			contact.update_last_seen() #TODO: is this necessary?
			if contact in pr:
				#remove from pending removal list, put back in contacts
				idx = pr.index(contact)
				old = self.pending_removal.pop(idx)[0]
				old.update_last_seen()
				self.contacts.append(old)
				#remove coresponding pending addition
				self.pending_addition.pop(idx)
			elif len(self.contacts) + len(self.pending_removal) < self.max_size:
				#there is space, so previously unseen contact can be added
				self.contacts.append(contact)
			elif len(self.contacts) > 0:
				#already have full set of contacts => must remove some
				oldest = self.contacts.pop(0)
				self.pending_removal.append((oldest, time.time() + ttl))
				self.pending_addition.append(contact)
				#NOTE: caller's responsibility to check if old node still online
				return oldest
				#otherwise, already have move than enought "fresh" contacts
				#pending addition, ignore new contact

	def empty(self):
		return len(self.contacts) == 0

	def __repr__(self):
		#TODO: have repr show pending removals + additions
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

	def update_route(self, contact, ttl=10):
		'''
		takes a just contacted node and updates the routing tables
		If lru contact is returned, caller must ping it.
		'''
		d = self.distance(contact.node_id)
		return self.buckets[bucket_index(d)].update(contact, ttl)

	def closest_nodes(self, node_id, k = 20):
		'''
		returns the k nodes in routing table closest to given node_id
		'''
		closest = []
		d = self.distance(node_id)
		idx = bucket_index(d)

		#use known "fresh" contacts over old ones
		closest.extend(self.buckets[idx].contacts)
		closest.extend(self.buckets[idx].pending_addition)

		i = 1
		#add nodes until we have >= k (or there are no more nodes left to add)
		while len(closest) < k and (idx - i >= 0 or idx + i < len(self.buckets)):
			if idx - i >= 0:
				closest.extend(self.buckets[idx - i].contacts)
				closest.extend(self.buckets[idx - i].pending_addition)
			if idx + i < len(self.buckets):
				closest.extend(self.buckets[idx + i].contacts)
				closest.extend(self.buckets[idx + i].pending_addition)
			i = i + 1
		#sort to get k closest
		#TODO: could be faster (computes xor too often)
		#TODO: add option to ignore specific node (ie: the requestor's id)
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

class Server(object):
	#message type codes
	ERROR = b'\x00'
	PING = b'\x01'
	PONG = b'\x02'
	STORE = b'\x03'
	STORE_SUCCESS = b'\x04'
	STORE_FAILURE = b'\x05'
	FIND_NODE = b'\x06'
	FIND_NODE_REPLY = b'\x07'
	FIND_VALUE = b'\x08'
	#if value not found, return results of find node
	#if value is small enough for a UPD packet, set it
	SMALL_VALUE_FOUND = b'\x09'
	#if value too big for one packet, have client fetch over TCP
	LARGE_VALUE_FOUND = b'\x0a'

	def __init__(self, node, verbose=True):
		self.node = node
		#TODO: make use of expiration
		#	add timers to periodically remove expired entries
		#	make store automatically determine expiration data
		self.store = KeyValueStore.KeyValueStore()
		self.client_addr = None
		self.message_type = None
		self.client_id = None
		self.transaction_id = None
		self.packet_data = None
		self.verbose = verbose
		self.udp_sock = None

	def log(self, message):
		if self.verbose:
			print(message)

	def send(self, code, message=b''):
		data = b''.join([code, self.node.node_id, self.transaction_id, message])
		self.udp_sock.sendto(data, self.client_addr)

	def send_error(self, error_message):
		if not self.transaction_id:
			self.transaction_id = b'\x00'*16
		self.send(Server.ERROR, error_message)

	def parse_header(self):
		'''
		Header format:
		1 byte message type
		32 byte sender id
		16 byte transaction id
		'''
		if len(self.packet_data) < 1 + 32 + 16:
			self.message_type = self.transaction_id = None
			self.log('client error: header is too short')
			self.send_error(b'header is too short')
			return 
		print(type(self.packet_data))
		self.message_type = self.packet_data[0:1]
		self.client_id = self.packet_data[1:33]
		self.transaction_id = self.packet_data[33:49]
		self.packet_data = self.packet_data[49:]
		self.log('Type: %d' % ord(self.message_type))
		self.log('Client id: %s' % self.client_id)
		self.log('Transaction id: %s' % self.transaction_id)

	def handle_ping(self):
		self.send(Server.PONG)

	def handle_pong(self):
		print("Got pong %s:%d", self.client_addr)
		#don't have to do anything except update routing table
		#(which happend automatically)
		pass

	def handle_find_node(self):
		'''
		packet format: headers || key
		Server returns list of 20 known nodes closest to given key
		Nodes given in format 32B node id || 4B IPv4 address || 2 byte port
		'''
		if len(self.packet_data) != 32:
			self.log('client error: key is wrong length')
			self.send_error(b'key is wrong length')
			#TODO: Q: if packet malformed, should routing table still be updated?
			return 
		closest = self.node.closest_nodes(self.packet_data)
		#TODO: make sure client's id is not in the list (get 21 if client in list remove, then return 20)
		self.send(Server.FIND_NODE_REPLY, b''.join([c.encode() for c in closest]))

	def handle_find_value(self):
		'''
		packet format: headers || key
		If value corresponding to key is present, value is returned over udp if
		small enought. Otherwise a LARGE_VALUE_FOUND code is sent to tell
		client to fetch over TCP.
		If key not present, server returns results of a find_node
		'''
		if len(self.packet_data) != 32:
			self.log('client error: key is wrong length')
			self.send_error(b'key is wrong length')
			return
		key = self.packet_data
		if key in self.store:
			value = self.store[key]
			if len(value) <= 512:
				self.log('Find %s -> %s' % (key, value[:32]))
				#return value over udp if it's small enought
				self.send(Server.SMALL_VALUE_FOUND, value)
			else:
				self.log('Find %s -> %s [Too large to return]' % (key, value[:32]))
				#otherwise tell client to use TCP
				self.send(Server.LARGE_VALUE_FOUND)
		else:
			self.log('Value for %s not found' % key)
			self.handle_find_node()

	def handle_store(self):
		'''
		packet format: headers || key || value
		stores key, value pair
		'''
		if len(self.packet_data) < 32:
			self.log('client error: key too short')
			self.send_error(b'key is too short')
			return 
		key = self.packet_data[:32]
		value = self.packet_data[32:]
		self.log('Storing %s -> %s' % (key, value[:32]))
		self.store[key] = value
		self.send(Server.STORE_SUCCESS)

	def handle_udp(self, port):
		self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#TODO: add error handling
		self.udp_sock.bind(('', port))
		self.log('Listening on port %d' % port)
		while True:
			self.packet_data, self.client_addr = self.udp_sock.recvfrom(512)
			self.log('Packet from %s:%d %s' % (self.client_addr[0], self.client_addr[1], self.packet_data[:32]))
			self.parse_header()
			if not self.message_type: continue

			#TODO: could use dispatcher ie: {Server.PING: self.handle_ping, ....}
			print(self.message_type, Server.PING)
			if self.message_type == Server.PING:
				self.handle_ping()
			elif self.message_type == Server.PONG:
				self.handle_pong()
			elif self.message_type == Server.FIND_NODE:
				self.handle_find_node()
			elif self.message_type == Server.FIND_VALUE:
				self.handle_find_value()
			elif self.message_type == Server.STORE:
				self.handle_store()
			else:
				self.send_error(b'unknown message type')
				continue
			lru = self.node.update_route(Contact(self.client_id, *self.client_addr))
			if lru:
				#must contact old node to warn of impending removal
				#TODO: move this out of main loop
				self.client_addr = (lru.ip, lru.port)
				self.log('Pinging %s:%d to check liveness...' % self.client_addr)
				self.transaction_id = os.urandom(16)
				self.send(Server.PING)
			self.log(self.node.__repr__())

def usage(name):
	print('usage: %s <port>' % (name, ))
	sys.exit(1)

if __name__ == '__main__':
	if len(sys.argv) != 2 or not port_str_valid(sys.argv[1]):
		usage(sys.argv[0])
	s = Server(Node())
	s.handle_udp(int(sys.argv[1]))
