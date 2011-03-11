import telnetlib, struct

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
            
    def get(self, port, path):
        t = telnetlib.Telnet('localhost', port)
        t.write('get file://%s\n' % (path))
        status = t.read_until('\n')[:-1].split(' ')[0]
        data = None
        if status == 'ok':
            data = t.read_all()
        return (status, data)
        
if __name__ == '__main__':
    
    n = Novacom()
    
    for d in n.devices:
        print d
        
    print
    result = n.get(n.devices[1].port, '/etc/palm-build-info')
    print result
    print
    header = struct.unpack('<Ibb', result[1][0:6])
    print header
    print
    print result[1][6:header[2]]
    print
    packet = struct.unpack('<IIII', result[1][-16:])
    print packet
    