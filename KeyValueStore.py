import time

class Value:
	def __init__(self, value, expiration=-1):
		'''
		For values that never expire, set expiration to -1
		'''
		self.value = value
		self.expiration = expiration

	def expired(self):
		''' 
		Checks if key, value has expired
		'''
		if self.expiration == -1:
			return False
		return time.time() > self.expiration

class KeyValueStore:
	def __init__(self, default_ttl=-1):
		'''
		ttl of -1 means item never expires
		'''
		self.store = {}
		self.default_ttl = default_ttl

	def remove_expired(self):
		for k in list(self.store.keys()):
			if self.store[k].expired():
				del self.store[k]

	def __contains__(self, key):
		return key in self.store

	def __getitem__(self, key):
		return self.store[key].value

	def set(self, key, item, ttl):
		'''
		ttl of -1 means item never expires
		'''
		if ttl == -1:
			expiration = -1;
		else:
			expiration = ttl + time.time()
		self.store[key] = Value(item, expiration)

	def __setitem__(self, key, item):
		'''
		sets value of item using default ttl
		'''
		self.set(key, item, self.default_ttl)
