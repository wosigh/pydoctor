#!/usr/bin/env python

import telnetlib, socket, struct, argparse, sys

class Device(object):
    
    def __init__(self, port, hash, connection, type):
        super(Device, self).__init__()
        self.port = port
        self.hash = hash
        self.connection = connection
        self.type = type
        
    def __str__(self):
        return "%d %s %s %s" % (self.port, self.hash, self.connection, self.type)

class Novacom(object):
    
    MAGIC = 0xdecafbad
    
    def __init__(self):
        super(Novacom, self).__init__()
        self.devices = [] 
        self.t = telnetlib.Telnet('localhost', 6968)
        self._get_devices()
        
    def _get_devices(self):
        for d in self.t.read_all()[:-1].split('\n'):
            d = d.split(' ')
            self.devices.append(Device(int(d[0]), d[1], d[2], d[3]))
            
    def put(self, port, path, data):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send('put file://%s\n' % (path))
        s.send(struct.pack('<IIII',self.MAGIC,1,len(data),0)+data)
        s.close()
            
    def get(self, port, path):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send('get file://%s\n' % (path))
        buf = []
        data = []
        c = s.recv(1)
        header = (0,0,0,0)
        while c != '\n':
            buf.append(c)
            c = s.recv(1)
        if "".join(buf).split(' ')[0] == 'ok':
            header = struct.unpack('<IIII', s.recv(16))
            while header[3] == 0:
                i = 0
                while i < header[2]:
                    data.append(s.recv(1))
                    i += 1
                header = struct.unpack('<IIII', s.recv(16))
            print header
            print [s.recv(header[2])]
        s.close()
        return "".join(data)
    
    def list_devices(self):
        for d in n.devices:
            print d

    def check_devices(self):
        if not len(self.devices) > 0:
            print 'unable to find device'
            sys.exit(1)
    
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-l','--list', action="store_true", dest="list", help='list devices')
    group1.add_argument('--get', dest="get", help='get a remote FILE from device', metavar='FILE')
    group1.add_argument('--put', dest="put", help='put a local FILE on device', metavar='FILE')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('--port', dest="port", help='connect to specific device by port', metavar='PORT')
    group2.add_argument('--nduid', dest="nduid", help='connect to specific device by nduid', metavar='NDUID')
    args = parser.parse_args()
    
    n = Novacom()
        
    if args.list:
        n.list_devices()
    elif args.get:
        n.check_devices()
        sys.stdout.write(n.get(n.devices[0].port, args.get))
    elif args.put:
        n.check_devices()
        data = sys.stdin.read()
        if data:
            n.put(n.devices[0].port, args.put, data)
    else:
        parser.print_help()

    