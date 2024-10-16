import sys
import select

class SockStream: 
    def __init__(self):
        self.buffer = b''

    def put_bytes(self, bytes):
        self.buffer += bytes

    def readline(self):
        if not self.can_read(): 
            return None
        out, remain = self.buffer.split(b'\n', 1)
        self.buffer = remain
        return out
        
    def can_read(self):
        if b'\n' in self.buffer: 
            return True
        return False

if __name__ == "__main__":
    stream = SockStream()
    stream.put_bytes(b"sdfsdfsdf")
    assert stream.readline() == None
    stream.put_bytes(b"xxx\nsss")
    assert stream.readline() == b'sdfsdfsdfxxx'
    stream.put_bytes(b"\n")
    assert stream.readline() == b'sss'

