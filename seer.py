import ipaddress
import math
import os.path
import pyglet
from pyglet.window import key, mouse
import requests
import shutil
import sys
import time

import apiserver
from campaign import Campaign
import resserver


class LocalResourceProvider(object):
    def __init__(self, top_dir):
        self.can_save = True
        self.top_dir = top_dir

    def open(self, path):
        path = os.path.join(self.top_dir, path)
        print('opening', path)
        return open(path, 'rb')

    def open_write(self, path):
        path = os.path.join(self.top_dir, path)
        print('writing', path)
        return open(path, 'w')

    def copy_file(self, src, dst):
        src = os.path.join(self.top_dir, src)
        dst = os.path.join(self.top_dir, dst)
        print('Backing up the campaign to', dst)
        shutil.copyfile(src, dst)


class RemoteResourceProvider(object):
    def __init__(self, address):
        self.can_save = False
        self.netloc = 'http://[{}]:{}/'.format(address, resserver.PORT)

    def open(self, path):
        print('opening', self.netloc + path)
        return requests.get(self.netloc + path, stream=True).raw


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
        self.show_veils = False
        self._veil_lines = []

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

        if self._veil_lines:
            pyglet.gl.glLineWidth(2)
            colors = [255, 255, 255] * (len(self._veil_lines) // 2 )
            pyglet.graphics.draw(len(self._veil_lines) // 2, pyglet.gl.GL_LINES,
                ('v2f', self._veil_lines),
                ('c3B', colors)
            )

    def _draw_veils(self):
        triangles = []
        colors = []
        if not self._campaign.is_master or not self.show_veils:
            self._veil_lines = []

        for veil in self._campaign.current_page.veils:
            if (not veil['covered'] and
                (not self._campaign.is_master or
                 not self.show_veils)): continue
            minx, miny = self.map_to_screen(veil['minx'], veil['miny'])
            maxx, maxy = self.map_to_screen(veil['maxx'], veil['maxy'])
            triangles.extend([
                minx, miny, maxx, miny, maxx, maxy,
                minx, maxy, minx, miny, maxx, maxy
            ])
            if self._campaign.is_master:
                if veil['covered']:
                    if self.show_veils:
                        colors.extend([128] * 18)
                    else:
                        colors.extend([64] * 18)
                else:
                    colors.extend([64] * 18)
                if self.show_veils:
                    self._veil_lines.extend([
                        minx, miny, maxx, miny,
                        maxx, miny, maxx, maxy,
                        maxx, maxy, minx, maxy,
                        minx, maxy, minx, miny
                    ])
            else:
                colors.extend([255] * 18)

        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_ONE, pyglet.gl.GL_ONE)
        pyglet.gl.glBlendEquation(pyglet.gl.GL_FUNC_REVERSE_SUBTRACT)

        pyglet.graphics.draw(len(triangles) // 2, pyglet.gl.GL_TRIANGLES,
            ('v2f', triangles),
            ('c3B', colors))
        pyglet.gl.glDisable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendEquation(pyglet.gl.GL_FUNC_ADD)


    def _draw_token(self, token):
            x, y = token.temp_position
            screen_x, screen_y = self.map_to_screen(x, y)
            token.fragment.sprite.update(
                x=screen_x, y=screen_y,
                scale=self._scale/token.fragment.resolution)
            token.fragment.sprite.draw()

    def draw(self):
        self._update_pan()
        # Draw non-player tokens
        for token in self._campaign.current_page.tokens:
            if token.player is None:
                self._draw_token(token)
        self._draw_veils()
        if self._show_grid:
            self._draw_grid()
        # Draw player tokens
        for token in self._campaign.current_page.tokens:
            if token.player is not None:
                self._draw_token(token)


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
        if self.is_master:
            if modifier & key.MOD_ACCEL:
                self.map.show_veils = True
            else:
                self.map.show_veils = False

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
        elif symbol == key.P and self.is_master:
            self.campaign.set_players_page(self.campaign.master_page)
        else:
            return

        # Unless we are in 'else' branch, return True to show that event was
        # consumed.
        return True

    def on_key_release(self, symbol, modifier):
        if self.is_master:
            if modifier & key.MOD_ACCEL:
                self.map.show_veils = True
            else:
                self.map.show_veils = False

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

        if modifiers & key.MOD_ACCEL:
            if self.is_master:
                self.campaign.current_page.toggle_veil(x, y)
            return

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
        self._dragging_token.move_temp(dx, dy)

        return True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT and self._dragging_token is not None:
            align = modifiers & (key.LSHIFT | key.RSHIFT)
            self._dragging_token.position_from_temp(align=align)
            self._dragging_token = None

    def on_api_request(self, request, client_address):
        method = request['method']
        print('on_api_request', method, 'from', client_address)
        params = request['params']
        if method == 'hi':
            print('Adding player {} at address {}'.format(
                params['player'], client_address))
            self.api_server.add_player(client_address)
        elif method == 'update_token':
            token = params['token']
            self.campaign.tokens[token['id']].update_data(
                token, notify=self.is_master)
        elif method == 'token_temp_position_changed':
            token = self.campaign.tokens[params['token_id']]
            position = params['position']
            if token is not self._dragging_token:
                token.set_temp_position(
                    position[0], position[1], notify=self.is_master)
            else:
                print('ignored')
        elif method == 'page_changed':
            self.campaign.set_players_page(params['players_page'])
            self.map.scale_to_fit(self.window.width, self.window.height)
        elif method == 'veils_updated':
            page_id = params['page_id']
            veils = params['veils']
            self.campaign.pages[page_id].set_veils(veils)
        else:
            print('Unknown API request:', request, 'from', client_address)

    def on_token_updated(self, token):
        print('on_token_updated:', token._data)
        notification = {
            'method': 'update_token',
            'params': {
                'token': token._data
            }
        }
        self.api_server.notify(notification)

    def on_token_temp_position_changed(self, token_id, position):
        print('on_token_temp_position_changed:', token_id, position)
        notification = {
            'method': 'token_temp_position_changed',
            'params': {
                'token_id': token_id,
                'position': position
            }
        }
        self.api_server.notify(notification)


    def on_page_changed(self, players_page):
        if not self.is_master: return
        print('on_page_changed', players_page)
        notification = {
            'method': 'page_changed',
            'params': {
                'players_page': players_page
            }
        }
        self.api_server.notify(notification)

    def on_veils_updated(self, page_id, veils):
        print('on_veils_updated, page', page_id)
        notification = {
            'method': 'veils_updated',
            'params': {
                'page_id': page_id,
                'veils': veils
            }
        }
        self.api_server.notify(notification)


def master_main(campaign_dir):
    ip = requests.get('https://api6.ipify.org').text
    print('Address: {}'.format(ip))

    resource_provider = LocalResourceProvider(campaign_dir)
    campaign = Campaign(resource_provider, None)
    window = pyglet.window.Window(resizable=True)
    res_server = resserver.ResourceServer(campaign_dir, campaign)
    api_server = apiserver.ApiServer(window)

    manager = Manager(window, campaign, api_server, None)

    pyglet.app.run()

    campaign.save()

    api_server.shutdown()
    res_server.shutdown()
    api_server.join()
    res_server.join()


def player_main(address, player):
    address = ipaddress.ip_address(address)
    assert address.version == 6
    master_address = address.exploded

    window = pyglet.window.Window(resizable=True)

    api_server = apiserver.ApiServer(window, master_address)
    request = {
        'id': 1,
        'method': 'hi',
        'params': {'player': player}
    }
    api_server.send(request)

    resource_provider = RemoteResourceProvider(master_address)
    campaign = Campaign(resource_provider, player)
    manager = Manager(window, campaign, api_server, player)

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
