import ipaddress
import math
import os.path
import pyglet
from pyglet.window import key, mouse
from pyglet.event import EVENT_HANDLED, EVENT_UNHANDLED
import requests
import shutil
import sys
import time

import apiserver
from campaign import Campaign
from map import Map
import resserver
import ui


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


class Manager(object):
    def __init__(self, window, campaign, api_server, player):
        self.campaign = campaign
        self.campaign.push_handlers(self)
        self.window = window
        self.window.push_handlers(self)
        self.focus_manager = ui.FocusManager(window)

        self.layout = ui.StackLayout(ui.Orientation.HORIZONTAL, window)
        sidebar = ui.StackLayout(
            ui.Orientation.VERTICAL, content_width=200)
        self.layout.add_child(sidebar)
        sidebar.add_child(ui.Pane(background=(64, 64, 64)))
        chat_input = ui.TextInput(
            content_height=200, background=(128, 128, 128))
        sidebar.add_child(chat_input)
        self.focus_manager.add_input(chat_input)

        self.map = Map(campaign, player)
        self.layout.add_child(self.map)

        self.api_server = api_server
        self.player = player
        # Make sure that on_draw is called regularly.
        pyglet.clock.schedule_interval(lambda _: None, 1 / 120)

    @property
    def is_master(self):
        return self.player is None

    @property
    def pan_speed(self):
        return max(self.window.width, self.window.height)

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
            self.map.scale_to_fit()
        elif symbol == key.PAGEUP and self.is_master:
            self.campaign.prev_page()
            self.map.scale_to_fit()
        elif symbol == key.P and self.is_master:
            self.campaign.set_players_page(self.campaign.master_page)
        else:
            return EVENT_UNHANDLED

        # Unless we are in 'else' branch, return True to show that event was
        # consumed.
        return EVENT_HANDLED

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
            if token is not self.map._dragging_token:
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
