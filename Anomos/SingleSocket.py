import socket
from errno import EWOULDBLOCK
from Anomos import bttime
from Anomos import INFO, CRITICAL, WARNING
from M2Crypto import SSL

try:
    from select import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1000
except ImportError:
    from Anomos.selectpoll import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1

class SingleSocket(object):

    def __init__(self, rawserver, sock, handler, context, ip=None):
        self.rawserver = rawserver
        self.socket = sock
        self.handler = handler
        self.context = context
        self.buffer = []
        self.last_hit = bttime()
        self.fileno = sock.fileno()
        self.connected = False
        self.peer_cert = sock.get_peer_cert()
        if ip is not None:
            self.ip = ip
            self.local = True
        else: # Try to get the IP from the socket
            self.local = False
            try:
                peername = self.socket.getpeername()
            except SSL.SSLError:
                self.ip = 'unknown'
            else:
                try:
                    self.ip = peername[0]
                except:
                    assert isinstance(peername, basestring)
                    self.ip = peername # UNIX socket, not really ip

    def recv(self, bufsize=65536):
        return self.socket.recv(bufsize)

    def _set_shutdown(self, opt=SSL.SSL_RECEIVED_SHUTDOWN|SSL.SSL_SENT_SHUTDOWN):
        self.socket.set_shutdown(opt)

    def _clear_state(self):
        self.socket = None
        self.buffer = []
        self.handler = None
        self.connected = False

    def close(self):
        if self.socket is not None:
            self._set_shutdown()
            self.socket.close()
            self._clear_state()
            del self.rawserver.single_sockets[self.fileno]
            self.rawserver.poll.unregister(self.fileno)

    def is_flushed(self):
        return len(self.buffer) == 0

    def write(self, s):
        if self.socket is not None:
            self.buffer.append(s)
            if len(self.buffer) == 1:
                self.try_write()
        else:
            self.rawserver.dead_from_write.append(self)

    def try_write(self):
        if self.connected:
            try:
                while self.buffer:
                    amount = self.socket.send(self.buffer[0])
                    if amount != len(self.buffer[0]):
                        if amount != 0:
                            self.buffer[0] = self.buffer[0][amount:]
                        break
                    del self.buffer[0]
            except SSL.SSLError, e:
                code, msg = e
                if code != EWOULDBLOCK:
                    #self.rawserver.add_task(self.rawserver._safe_shutdown, self)
                    self.rawserver.dead_from_write.append(self)
                    return
        if self.buffer == []:
            self.rawserver.poll.register(self.socket, POLLIN)
        else:
            self.rawserver.poll.register(self.socket, POLLIN | POLLOUT)
