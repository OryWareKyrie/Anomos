# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import traceback

from Anomos import LOG as log
from Anomos.AnomosNeighborInitializer import AnomosNeighborInitializer
from Anomos.P2PConnection import P2PConnection
from M2Crypto import SSL

class P2PServer(SSL.ssl_dispatcher):
    def __init__(self, addr, port, ssl_context):
        SSL.ssl_dispatcher.__init__(self)
        self.create_socket(ssl_context)
        self.socket.setblocking(0)
        self.set_reuse_addr()
        #TODO: move port testing (_find_port) from download.py
        # to here.
        self.bound = False     # The bound variable is to prevent handle_error
        self.bind((addr, port))# from logging errors caused by the following
        self.bound = True      # call to bind. Errors from bind are caught by
                               # _find_port in Multitorrent.
        self.listen(10) # TODO: Make this queue length a configuration option
                        # or determine a best value for it
        self.socket.set_post_connection_check_callback(lambda x,y: x != None)

        # Neighbor Manager is set after the torrent is started
        self.neighbor_manager = None

    def set_neighbor_manager(self, mgr):
        self.neighbor_manager = mgr

    ## asyncore.dispatcher methods ##

    def writable(self):
        return False

    def handle_accept(self):
        if self.neighbor_manager is None:
            #XXX: What's the proper behavior here?
            return
        try:
            sock, addr = self.socket.accept()
        except SSL.SSLError, err:
            if "unexpected eof" not in err:
                self.handle_error()
            return

        self.log(str(self))
        #if (self.ssl_ctx.get_verify_mode() is SSL.verify_none) or sock.verify_ok():
        conn = P2PConnection(socket=sock)
        AnomosNeighborInitializer(self.neighbor_manager, conn)
        #else:
        #    print 'peer verification failed'
        #    sock.close()

    def handle_connect(self):
        # Connect for this socket implies it tried to bind
        # to a port which was already in use.
        self.close()

    def handle_error(self):
        #if self.bound:
        log.critical('\n'+traceback.format_exc())
        self.close()

    def handle_expt(self):
        log.critical('\n'+traceback.format_exc())
        self.close()

