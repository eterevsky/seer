import http.server
import socket
import socketserver
import threading

PORT = 2215


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=server.dir)


class ResourceServerImpl(socketserver.TCPServer):
    address_family = socket.AF_INET6

    def __init__(self, dir):
        self.dir = dir
        super().__init__(('::', PORT), RequestHandler)


class ResourceServer(threading.Thread):
    def __init__(self, campaign_dir):
        self.httpd = ResourceServerImpl(campaign_dir)
        super().__init__()
        self.start()

    def run(self):
        print('Starting ResourceServer on port', PORT)
        self.httpd.serve_forever()
        print('Stopped ResourcesServer')
        self.httpd.server_close()

    def shutdown(self):
        self.httpd.shutdown()
