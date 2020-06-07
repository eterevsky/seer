import json
import pyglet
import socket
import socketserver
import threading

import event

PORT = 2214
CLIENT_PORT = 2216


class ApiServerImpl(socketserver.UDPServer):
    address_family = socket.AF_INET6

    def __init__(self, event_dispatcher, is_master, port):
        self.platform_event_loop = pyglet.app.platform_event_loop
        self.platform_event_loop.start()
        self.event_dispatcher = event_dispatcher
        if port is None:
            port = PORT if is_master else CLIENT_PORT
        super().__init__(('::', port), None)

    def finish_request(self, request, client_address):
        self.platform_event_loop.post_event(
            self.event_dispatcher, 'on_api_request_raw', request, client_address)


class ApiServer(threading.Thread, event.EventDispatcher):
    def __init__(self,master=None, port=None):
        self.server = ApiServerImpl(
            self, is_master=(master is None), port=port)
        if type(master) is str:
            master = (master, PORT)
        self.master = master
        self.players = set()
        super().__init__()
        self.start()

    def run(self):
        print('Starting ApiServer on port', PORT)
        self.server.serve_forever()
        print('Stopped ApiServer')
        self.server.server_close()

    def shutdown(self):
        self.server.shutdown()

    def on_api_request_raw(self, request, client_address):
        print('on_api_request_raw', request)
        self.players.add(client_address)
        request = json.loads(request[0])
        self.dispatch_event('on_api_request', request, client_address)

    def send(self, request, address=None):
        if address is None: address = self.master
        assert address is not None
        request = json.dumps(request).encode('utf-8')
        self.server.socket.sendto(request, address)

    def add_player(self, address):
        self.players.add(address)

    def notify(self, request):
        request = json.dumps(request).encode('utf-8')
        if self.master is not None:
            print('notify master', request)
            self.server.socket.sendto(request, self.master)
        else:
            for address in self.players:
                print('notify', address, request)
                self.server.socket.sendto(request, address)

ApiServer.register_event_type('on_api_request_raw')
ApiServer.register_event_type('on_api_request')
