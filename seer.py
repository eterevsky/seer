import ipaddress
import math
import json
import os.path
import pyglet
from pyglet.window import key, mouse
import requests
import sys
import time

import apiserver
import resserver


class LocalResourceProvider(object):
    def __init__(self, top_dir):
        self.top_dir = top_dir

    def open(self, path):
        print('opening', os.path.join(self.top_dir, path))
        return open(os.path.join(self.top_dir, path), 'rb')


class RemoteResourceProvider(object):
    def __init__(self, address):
        self.netloc = 'http://[{}]:{}/'.format(address, resserver.PORT)

    def open(self, path):
        print('opening', self.netloc + path)
        return requests.get(self.netloc + path, stream=True).raw


class Fragment(object):
    """A sprite representing a token or a map tile.

    May contain the default values for controlling player and position.
    """

    def __init__(self, config, provider, id):
        self.id = id
        self._config = config
        fname = os.path.basename(config['path'])
        with provider.open(config['path']) as file:
            img = pyglet.image.load(fname, file=file)
        self._img_width = img.width
        self._img_height = img.height
        self.sprite = pyglet.sprite.Sprite(img=img, subpixel=True)

    @property
    def position(self) -> (float, float):
        return self._config.get('position', (0, 0))

    @property
    def type(self) -> str:
        return self._config['type']

    @property
    def player(self):
        return self._config.get('player', None)

    @property
    def width(self) -> float:
        if 'width' in self._config:
            return self._config['width']
        else:
            return self.sprite.width / self._config['resolution']

    @property
    def height(self) -> float:
        if 'height' in self._config:
            return self._config['height']
        else:
            return self._img_height / self._config['resolution']

    @property
    def size(self) -> (float, float):
        return self.width, self.height

    @property
    def resolution(self) -> float:
        if 'resolution' in self._config:
            return self._config['resolution']
        else:
            return self._img_width / self.width


class Token(object):
    """A token or a map tile added to a page.

    Contains the fragment that is drawn with its position. A single fragment
    can be added multiple times to one or more maps. Each such instance has
    the same `Fragment`, but separate Token.
    """

    def __init__(self, config, fragment, dispatcher):
        self._config = config
        self.fragment = fragment
        self._dispatcher = dispatcher
        self._dispatcher.register_event_type('on_token_updated')

    def _update(self):
        self._dispatcher.dispatch_event('on_token_updated', self)

    def update_config(self, config):
        self._config = config

    @property
    def position(self):
        return self._config.get('position', self.fragment.position)

    @property
    def type(self):
        return self._config.get('type', self.fragment.type)

    @property
    def player(self):
        return self._config.get('player', self.fragment.player)

    @property
    def is_token(self):
        return self.type.startswith('token')

    def set_position(self, x, y):
        self._config['position'] = (x, y)
        self._update()

    @property
    def id(self):
        return self._config['id']

    def controlled_by(self, player):
        return player is None or player == self.player

    def move(self, dx, dy):
        x, y = self._config['position']
        self._config['position'] = (x + dx, y + dy)
        self._update()

    def align_to_grid(self):
        x, y = self._config['position']
        x, y = round(x), round(y)
        self._config['position'] = (x, y)
        self._update()


class Page(object):
    def __init__(self, config, campaign):
        self._config = config
        self.tokens = []
        for token_cfg in config['tokens']:
            token = Token(token_cfg,
                          campaign.fragments[token_cfg['fragment_id']],
                          campaign)
            self.tokens.append(token)


class Campaign(pyglet.event.EventDispatcher):
    def __init__(self, resource_provider):
        self._resource_provider = resource_provider
        with resource_provider.open('data.json') as data:
            self._data = json.load(data)
        self.fragments = {}
        for id, frag_config in self._data['fragments'].items():
            self.fragments[id] = Fragment(frag_config, self._resource_provider, id)
        self.pages = []
        self.tokens = {}
        for page_cfg in self._data['pages']:
            page = Page(page_cfg, self)
            self.pages.append(page)
            for token in page.tokens:
                self.tokens[token.id] = token
        self._current_page = 0

    @property
    def current_page(self):
        return self.pages[self._current_page]

    def find_token(self, x, y) -> Token:
        for token in self.current_page.tokens:
            if token.is_token:
                tx, ty = token.position
                if (tx <= x <= tx + token.fragment.width and
                    ty <= y <= ty + token.fragment.height):
                    return token
        return None

    def next_page(self):
        if self._current_page + 1 < len(self.pages):
            self._current_page += 1

    def prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1


class Map(object):
    def __init__(self, campaign):
        self._campaign = campaign
        self._tx = 0
        self._ty = 0
        self._scale = 70
        self._screen_width = None
        self._screen_height = None
        self._pan_speed_x = 0
        self._pan_speed_y = 0
        self._show_grid = True
        self._last_pan_update = time.time()

    def _bounding_box(self):
        minx, maxx = 1E6, -1E6
        miny, maxy = 1E6, -1E6
        for token in self._campaign.current_page.tokens:
            x0, y0 = token.position
            if x0 < minx: minx = x0
            if y0 < miny: miny = y0
            w, h = token.fragment.size
            if x0 + w > maxx: maxx = x0 + w
            if y0 + h > maxy: maxy = y0 + h
        return minx, maxx, miny, maxy

    def screen_to_map(self, screen_x, screen_y):
        """Convert screen coordinates to map coordinates."""
        return ((screen_x - self._tx) / self._scale,
                (screen_y - self._ty) / self._scale)

    def screen_to_map_delta(self, screen_dx, screen_dy):
        """Convert screen coordinates to map coordinates."""
        return screen_dx / self._scale, screen_dy / self._scale

    def map_to_screen(self, x, y):
        return x * self._scale + self._tx, y * self._scale + self._ty

    def scale_to_fit(self, screen_width, screen_height):
        if not self._campaign.fragments:
            self._tx = 0
            self._ty = 0
            self._scale = 70
            return

        self._screen_width = screen_width
        self._screen_height = screen_height

        minx, maxx, miny, maxy = self._bounding_box()

        width = maxx - minx
        height = maxy - miny
        scalex = screen_width / width
        scaley = screen_height / height
        self._scale = min(scalex, scaley)
        self._tx = (screen_width - width * self._scale) / 2 - minx * self._scale
        self._ty = (screen_height - height * self._scale) / 2 - miny * self._scale

    def zoom(self, screen_x, screen_y, zoom):
        self._scale *= zoom
        self._tx = screen_x - zoom * (screen_x - self._tx)
        self._ty = screen_y - zoom * (screen_y - self._ty)

    def _update_pan(self):
        t = time.time()
        self._tx += (t - self._last_pan_update) * self._pan_speed_x
        self._ty += (t - self._last_pan_update) * self._pan_speed_y
        self._last_pan_update = t

    def pan_vertical(self, speed):
        self._update_pan()
        self._pan_speed_y = speed

    def pan_horizontal(self, speed):
        self._update_pan()
        self._pan_speed_x = speed

    def toggle_grid(self):
        self._show_grid = not self._show_grid

    def _draw_grid(self):
        w, h = self._screen_width, self._screen_height

        minx, miny = self.screen_to_map(0, 0)
        maxx, maxy = self.screen_to_map(w, h)

        def draw_lines(check, width):
            lines = []

            for x in range(math.ceil(minx), math.floor(maxx) + 1):
                if not check(x): continue
                screenx, _ = self.map_to_screen(x, 0)
                lines.extend([screenx, 0, screenx, h])

            for y in range(math.ceil(miny), math.floor(maxy) + 1):
                if not check(y): continue
                _, screeny = self.map_to_screen(0, y)
                lines.extend([0, screeny, w, screeny])

            colors = [127, 127, 127] * (len(lines) // 2)
            pyglet.gl.glLineWidth(width)
            pyglet.graphics.draw(len(lines) // 2, pyglet.gl.GL_LINES,
                ('v2f', lines),
                ('c3B', colors)
            )

        draw_lines(lambda x: x % 5 != 0, 1)
        draw_lines(lambda x: x % 10 == 5, 2)
        draw_lines(lambda x: x % 10 == 0, 3)

    def _draw_token(self, token):
            x, y = token.position
            screen_x, screen_y = self.map_to_screen(x, y)
            token.fragment.sprite.update(
                x=screen_x, y=screen_y,
                scale=self._scale/token.fragment.resolution)
            token.fragment.sprite.draw()

    def draw(self):
        self._update_pan()
        for token in self._campaign.current_page.tokens:
            self._draw_token(token)
        if self._show_grid:
            self._draw_grid()


class Manager(object):
    def __init__(self, window, campaign, api_server, player):
        self.campaign = campaign
        self.campaign.push_handlers(self)
        self.window = window
        self.window.push_handlers(self)
        self.map = Map(campaign)
        self.map.scale_to_fit(window.width, window.height)
        self.api_server = api_server
        self.player = player
        # self.api_server.push_handlers(self)
        self._dragging_token = None
        # Make sure that on_draw is called regularly.
        pyglet.clock.schedule_interval(lambda _: None, 1 / 120)

    @property
    def is_master(self):
        return self.player is None

    @property
    def pan_speed(self):
        return max(self.window.width, self.window.height)

    def on_draw(self):
        self.window.clear()
        self.map.draw()

    def on_key_press(self, symbol, modifier):
        if symbol == key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
        elif symbol == key.W:
            self.map.pan_vertical(-self.pan_speed)
        elif symbol == key.A:
            self.map.pan_horizontal(self.pan_speed)
        elif symbol == key.S:
            self.map.pan_vertical(self.pan_speed)
        elif symbol == key.D:
            self.map.pan_horizontal(-self.pan_speed)
        elif symbol == key.G:
            self.map.toggle_grid()
        elif symbol == key.PAGEDOWN and self.is_master:
            self.campaign.next_page()
            self.map.scale_to_fit(self.window.width, self.window.height)
        elif symbol == key.PAGEUP and self.is_master:
            self.campaign.prev_page()
            self.map.scale_to_fit(self.window.width, self.window.height)
        else:
            return

        # Unless we are in 'else' branch, return True to show that event was
        # consumed.
        return True

    def on_key_release(self, symbol, modifier):
        if symbol in (key.A, key.D):
            self.map.pan_horizontal(0)
        elif symbol in (key.W, key.S):
            self.map.pan_vertical(0)
        else:
            return

        return True

    def on_resize(self, width, height):
        self.map.scale_to_fit(width, height)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.map.zoom(x, y, 1.1 ** (-scroll_y))

    def on_mouse_press(self, screenx, screeny, button, modifiers):
        if button != mouse.LEFT:
            print('left button not pressed')
            return

        x, y = self.map.screen_to_map(screenx, screeny)
        token = self.campaign.find_token(x, y)
        if token is not None and token.controlled_by(self.player):
            self._dragging_token = token

    def on_mouse_drag(self, screenx, screeny, screen_dx, screen_dy, buttons, modifiers):
        if not (buttons & mouse.LEFT):
            print('left button not pressed')
            return

        if self._dragging_token is None:
            print('No currently draggable token')
            return

        dx, dy = self.map.screen_to_map_delta(screen_dx, screen_dy)
        self._dragging_token.move(dx, dy)

        return True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT and self._dragging_token is not None:
            if modifiers & (key.LSHIFT | key.RSHIFT):
                self._dragging_token.align_to_grid()
            self._dragging_token = None

    def on_api_request(self, request, client_address):
        print('on_api_request', request, 'from', client_address)
        method = request['method']
        params = request['params']
        if method == 'hi':
            print('Adding player {} at address {}'.format(
                params['name'], client_address))
            self.api_server.add_player(client_address)
        elif method == 'update_token':
            token = params['token']
            self.campaign.tokens[token['id']].update_config(token)

    def on_token_updated(self, token):
        print('on_token_updated:', token._config)
        notification = {
            'method': 'update_token',
            'params': {
                'token': token._config
            }
        }

        self.api_server.notify(notification)


def master_main(campaign_dir):
    ip = requests.get('https://api6.ipify.org').text
    print('Address: {}'.format(ip))

    window = pyglet.window.Window(resizable=True)
    res_server = resserver.ResourceServer(campaign_dir)
    api_server = apiserver.ApiServer(window)

    resource_provider = LocalResourceProvider(campaign_dir)
    campaign = Campaign(resource_provider)
    manager = Manager(window, campaign, api_server, None)

    pyglet.app.run()

    api_server.shutdown()
    res_server.shutdown()
    api_server.join()
    res_server.join()


def player_main(address, name):
    address = ipaddress.ip_address(address)
    assert address.version == 6
    master_address = address.exploded

    window = pyglet.window.Window(resizable=True)

    api_server = apiserver.ApiServer(window, master_address)
    request = {
        'id': 1,
        'method': 'hi',
        'params': {'name': name}
    }
    api_server.send(request)

    resource_provider = RemoteResourceProvider(master_address)
    campaign = Campaign(resource_provider)
    manager = Manager(window, campaign, api_server, name)

    pyglet.app.run()

    api_server.shutdown()
    api_server.join()


HELP = """
Usage:
    python seer.py <campaign directory>
or
    python seer.py <master IPv6 address> <your name>
"""

if __name__ == '__main__':
    if len(sys.argv) == 2:
        master_main(sys.argv[1])
    elif len(sys.argv) == 3:
        player_main(sys.argv[1], sys.argv[2])
    else:
        print(HELP)
