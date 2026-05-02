import socket, time, hashlib, struct, bencodepy, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')

PROXY = ('127.0.0.1', 6244)

def proxy_connect(host, port, timeout=15):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(PROXY)
    sock.sendall(('CONNECT %s:%d HTTP/1.0\r\nHost: %s:%d\r\n\r\n' % (host, port, host, port)).encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        resp += sock.recv(4096)
    if b'200' not in resp:
        sock.close()
        return None
    return sock

# Step 1: Get torrent
print('Step 1: Fetch torrent...')
torrent_url = 'https://annas-archive.gd/dyn/small_file/torrents/managed_by_aa/annas_archive_meta__aacid/annas_archive_meta__aacid__duxiu_files__20240613T170516Z--20250127T144745Z.jsonl.seekable.zst.torrent'
p = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:6244', 'https': 'http://127.0.0.1:6244'})
opener = urllib.request.build_opener(p)
data = opener.open(urllib.request.Request(torrent_url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read()
torrent = bencodepy.decode(data)
info = torrent[b'info']
info_hash = hashlib.sha1(bencodepy.encode(info)).digest()
peer_id = b'-BD0001-' + bytes(range(12))
print('Info hash:', info_hash.hex())

# Step 2: Announce to tracker
print('\nStep 2: Announce...')
ih_enc = ''.join('%{:02x}'.format(b) for b in info_hash)
pid_enc = ''.join('%{:02x}'.format(b) for b in peer_id)
params = 'info_hash=' + ih_enc + '&peer_id=' + pid_enc
params += '&port=6881&uploaded=0&downloaded=0&left=' + str(info[b'length'])
params += '&event=started&compact=1&numwant=200'

sock = proxy_connect('tracker.bt4g.com', 2095)
if not sock:
    print('Failed to connect to tracker')
    sys.exit(1)

get_req = 'GET /announce?' + params + ' HTTP/1.0\r\nHost: tracker.bt4g.com:2095\r\nUser-Agent: BD/1.0\r\nConnection: close\r\n\r\n'
sock.sendall(get_req.encode())
t0 = time.time()
data = b''
while time.time() - t0 < 15:
    try:
        sock.settimeout(3)
        c = sock.recv(65536)
        if not c: break
        data += c
    except: break
sock.close()

body = data[data.find(b'\r\n\r\n') + 4:]
d = bencodepy.decode(body)
peers_raw = d[b'peers']
peers = []
for i in range(0, len(peers_raw), 6):
    ip = '.'.join(str(b) for b in peers_raw[i:i+4])
    p = struct.unpack('!H', peers_raw[i+4:i+6])[0]
    peers.append((ip, p))
print('Got %d peers' % len(peers))

# Step 3: Connect to peers and try download piece 0
print('\nStep 3: Downloading piece 0...')
pieces_hash = info[b'pieces']
piece_len = info[b'piece length']

for ip, port in peers[:20]:
    sock = proxy_connect(ip, port, 10)
    if not sock:
        continue
    
    # Handshake - use simple reserved bytes
    hs = b'\x13BitTorrent protocol' + b'\x00' * 8 + info_hash + peer_id
    sock.sendall(hs)
    
    try:
        sock.settimeout(10)
        hs_resp = b''
        while len(hs_resp) < 68:
            c = sock.recv(68 - len(hs_resp))
            if not c: 
                print('  Handshake recv empty at %d bytes' % len(hs_resp))
                raise Exception('handshake truncated')
            hs_resp += c
        
        if hs_resp[0] != 19:
            print('  Bad handshake: first byte=%d' % hs_resp[0])
            sock.close(); continue
        remote_id = hs_resp[48:68]
        print('  Handshake OK with %s:%d remote=%s' % (ip, port, remote_id.hex()))
        
        # Wait for messages (bitfield + unchoke)
        sock.sendall(struct.pack('!IB', 1, 2))  # interested
        
        unchoked = False
        for _ in range(30):
            try:
                sock.settimeout(3)
                hdr = b''
                while len(hdr) < 4:
                    c = sock.recv(4 - len(hdr))
                    if not c: break
                    hdr += c
                if len(hdr) < 4: break
                msg_len = struct.unpack('!I', hdr)[0]
                if msg_len == 0: continue
                body_bytes = b''
                while len(body_bytes) < msg_len:
                    body_bytes += sock.recv(msg_len - len(body_bytes))
                
                if body_bytes[0] == 1:  # unchoke
                    unchoked = True
                    print('    Unchoked!')
                    break
                elif body_bytes[0] == 0:  # choke
                    print('    Choked')
                    break
            except socket.timeout:
                pass
            except Exception:
                break
        
        if not unchoked:
            sock.close(); continue
        
        # Request block from piece 0
        block_size = 16384
        first_piece_size = min(piece_len, info[b'length'])
        req = struct.pack('!I', 13) + b'\x06' + struct.pack('!III', 0, 0, min(block_size, first_piece_size))
        sock.sendall(req)
        
        # Receive piece
        sock.settimeout(30)
        hdr = b''
        while len(hdr) < 4:
            c = sock.recv(4 - len(hdr))
            if not c: break
            hdr += c
        if len(hdr) < 4:
            print('    No piece received'); sock.close(); continue
        
        msg_len = struct.unpack('!I', hdr)[0]
        body_bytes = b''
        while len(body_bytes) < msg_len:
            body_bytes += sock.recv(msg_len - len(body_bytes))
        
        if body_bytes[0] == 7:  # piece
            piece_idx = struct.unpack('!I', body_bytes[1:5])[0]
            begin = struct.unpack('!I', body_bytes[5:9])[0]
            block_data = body_bytes[9:]
            print('    GOT BLOCK! piece=%d begin=%d size=%d' % (piece_idx, begin, len(block_data)))
            print('    First bytes:', block_data[:50].hex())
            
            if block_data[:4] == b'\x28\xb5\x2f\xfd':
                print('    ** ZSTANDARD MAGIC DETECTED **')
            
        sock.close()
        break
    except Exception as e:
        print('    Error: %s %s' % (type(e).__name__, str(e)[:80]))
        try: sock.close()
        except: pass