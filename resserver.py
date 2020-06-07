import http.server
from http import HTTPStatus
import json
import pyglet
import queue
import socket
import socketserver
import threading

PORT = 2215


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=server.dir)

    def do_GET(self):
        print(self.path)
        if self.path == '/data.json':
            self.server.platform_event_loop.post_event(
                self.server.dispatcher, 'on_request_data')
            data = self.server.data_queue.get()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()


class ResourceServerImpl(socketserver.TCPServer):
    address_family = socket.AF_INET6

    def __init__(self, dir, dispatcher, data_queue):
        self.dir = dir
        self.dispatcher = dispatcher
        self.data_queue = data_queue
        self.platform_event_loop = pyglet.app.platform_event_loop
        super().__init__(('::', PORT), RequestHandler)


class ResourceServer(threading.Thread, pyglet.event.EventDispatcher):
    def __init__(self, campaign_dir, campaign):
        self.campaign = campaign
        self.data_queue = queue.Queue()
        self.httpd = ResourceServerImpl(campaign_dir, self, self.data_queue)
        super().__init__()
        self.start()

    def run(self):
        print('Starting ResourceServer on port', PORT)
        self.httpd.serve_forever()
        print('Stopped ResourcesServer')
        self.httpd.server_close()

    def shutdown(self):
        self.httpd.shutdown()

    def on_request_data(self):
        data = self.campaign._data
        data = json.dumps(data).encode('utf-8')
        self.data_queue.put(data)

ResourceServer.register_event_type('on_request_data')