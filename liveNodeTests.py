from Node import *
from struct import *
from socket import *

def sendto(data, addr=('localhost',9999)):
	s = socket(AF_INET, SOCK_DGRAM)
	s.sendto(data, addr)
	return s

def make_connections(start=0, end=30):
	'''
	make a bunch of connections with different node ids to populate routing table
	'''
	for i in range(start, end):
		sendto(b'\x01' + pack('<H', i)*24 + b'\x07'*32)

def query(code, m, node_id=b'\x01'*32):
	s = sendto(code + node_id + b'\xaa'*16 + m)
	return s.recvfrom(1000)
