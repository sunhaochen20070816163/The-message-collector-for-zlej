import base64
import queue
import hashlib
import json
import socket
import struct
import threading
import time
import urllib.parse
class wsmsg():
	def encode(data):
		data=data.encode('utf-8')
		ws_token=b'\x81'
		ws_len=len(data)
		if ws_len<126:
			ws_token+=struct.pack('B',ws_len)
		elif ws_len<=0xFFFF:
			ws_token+=struct.pack('!BH',126,ws_len)
		else:
			ws_token+=struct.pack('!BQ',127,ws_len)
		return ws_token+data
	def decode(data):
		ws_ismask=data[1]>128
		ws_payload_len=data[1]&127
		package_len=ws_payload_len+6
		if ws_payload_len == 126:
			extend_payload_len=data[2:4]
			package_len=int.from_bytes(extend_payload_len,'big')+8
			ws_mask=data[4:8]
			wscode=data[8:]
		elif ws_payload_len == 127:
			extend_payload_len=data[2:10]
			package_len=int.from_bytes(extend_payload_len,'big')+14
			ws_mask=data[10:14]
			wscode=data[14:]
		else:
			extend_payload_len=None
			ws_mask=data[2:6]
			wscode=data[6:]
		ws_recv=bytearray()
		for i in range(len(wscode)):
			ws_recv.append(wscode[i]^ws_mask[i%4])
		ws_recv=bytes(ws_recv)
		if data[0]&15==1:
			ws_recv=ws_recv.decode('utf-8',errors='ignore')
		return ws_recv
	def close(id=1000):
		return struct.pack('!B B H',0x88,0x02,id)
def rcvc(client,location,q):
	print(location,'online')
	try:
		while True:
			data=q.get()
			data=json.loads(data)
			if data['l']!=location:
				data={'location':data['l'],'username':data['u'],'content':data['c']}
				data=json.dumps(data)
				data=wsmsg.encode(data)
				client.sendall(data)
	except Exception as e:
		wsthreads.remove(threading.current_thread())
		print(location,'offline\t',e)
	return
def h(client,address):
	data=b''
	d=None
	while d!=b'' and not b'\r\n\r\n' in data:
		d=client.recv(1024)
		data+=d
	method,path,protocol=data.split(b'\r\n')[0].decode('utf-8',errors='ignore').split(' ',2)
	query={}
	if '?' in path:
		path,queryl=path.split('?',1)
		queryaslist=queryl.split('&')
		for i in queryaslist:
			query.update({urllib.parse.unquote(i.split('=')[0]):urllib.parse.unquote(i.split('=',1)[-1])})
	headers=data.split(b'\r\n\r\n')[0].decode('utf-8',errors='ignore')
	headersaslist=headers.split('\r\n')[1:]
	headers={}
	for i in headersaslist:
		headers[i.split(':')[0]]=i.split(':',1)[-1].strip()
	if len(data.split(b'\r\n\r\n',1))>1:
		data=data.split(b'\r\n\r\n',1)[1]
	global wsthreads
	if path=='/send':
		if 'location' in query and 'username' in query and 'content' in query:
			print(query['location'],'\t',query['username'],'\t',query['content'])
			for gts in wsthreads:
				gts._args[2].put(json.dumps({'l':query['location'],'u':query['username'],'c':query['content']}))
			client.sendall(protocol.encode('utf-8')+b' 200 OK\r\nServer: zlejs Developer Server\r\n\r\n')
		else:
			client.sendall(protocol.encode('utf-8')+b' 500 Query Not Found\r\nServer: zlejs Developer Server\r\n\r\n')
	elif path=='/ws' and 'location' in query and 'Sec-WebSocket-Key' in headers:
		client.sendall(b'HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Accept: '+base64.b64encode(hashlib.sha1((headers['Sec-WebSocket-Key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())+b'\r\n\r\n')
		wsthreads.append(threading.Thread(target=rcvc,args=(client,query['location'],queue.Queue())))
		wsthreads[len(wsthreads)-1].start()
		while True:
			if len(data)<6:
				d=client.recv(6-len(data))
				data+=d
				continue
			elif len(data)<8 and data[1]&127==126:
				d=client.recv(8-len(data))
				data+=d
				continue
			elif len(data)<14 and data[1]&127==127:
				d=client.recv(14-len(data))
				data+=d
				continue
			elif len(data)>=6 and len(data)<(data[1]&127)+6 and data[1]&127<126:
				d=client.recv((data[1]&127)+6-len(data))
				data+=d
				continue
			elif len(data)>=8 and len(data)<int.from_bytes(data[2:4],'big')+8 and data[1]&127==126:
				d=client.recv(int.from_bytes(data[2:4],'big')+8-len(data))
				data+=d
				continue
			elif len(data)>=14 and len(data)<int.from_bytes(data[2:10],'big')+14 and data[1]&127==127:
				d=client.recv(int.from_bytes(data[2:10],'big')+14-len(data))
				data+=d
				continue
			if d==b'':
				return
			data=wsmsg.decode(data)
			try:
				data=json.loads(data)
				print(query['location'],'\t',data['username'],'\t',data['content'])
				for gts in wsthreads:
					try:
						gts._args[2].put(json.dumps({'l':query['location'],'u':data['username'],'c':data['content']}))
					except:
						pass
			except Exception as e:
				print(query['location'],data,e)
			data=b''
	else:
		client.sendall(protocol.encode('utf-8')+b' 404 Not Found\r\nServer: zlejs Developer Browser\r\n\r\n')
	client.close()
if __name__=='__main__':
	print('HTTP/WS AT 32500')
	s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.bind(('0.0.0.0',32500))
	s.listen(64)
	wsthreads=[]
	while True:
		threading.Thread(target=h,args=s.accept()).start()