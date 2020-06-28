"""The representation of the shared game state."""

import datetime
import json
import os.path
import pyglet
import time

import saviour


class Fragment(object):
    """A sprite representing a token or a map tile.

    May contain the default values for controlling player and position.
    """

    def __init__(self, data, provider, id):
        self.id = id
        self._data = data
        fname = os.path.basename(data['path'])
        with provider.open(data['path']) as file:
            self.image = pyglet.image.load(fname, file=file).get_texture()

    @property
    def position(self) -> (float, float):
        return self._data.get('position', (0, 0))

    @property
    def type(self) -> str:
        return self._data['type']

    @property
    def player(self):
        return self._data.get('player', None)

    @property
    def width(self) -> float:
        if 'width' in self._data:
            return self._data['width']
        else:
            return self.image.width / self._data['resolution']

    @property
    def height(self) -> float:
        if 'height' in self._data:
            return self._data['height']
        else:
            return self.image.height / self._data['resolution']

    @property
    def size(self) -> (float, float):
        return self.width, self.height

    @property
    def resolution(self) -> float:
        if 'resolution' in self._data:
            return self._data['resolution']
        else:
            return self.image.width / self.width


class Token(object):
    """A token or a map tile added to a page.

    Contains the fragment that is drawn with its position. A single fragment
    can be added multiple times to one or more maps. Each such instance has
    the same `Fragment`, but separate Token.
    """

    def __init__(self, data, fragment, campaign):
        self._data = data
        self.fragment = fragment
        self._campaign = campaign
        self._temp_position = None

    def update_data(self, data, notify=False):
        self._data = data
        self._temp_position = None
        if notify:
            self._campaign.dispatch_event('on_token_updated', self)

    @property
    def id(self):
        return self._data['id']

    @property
    def temp_position(self):
        if self._temp_position is not None:
            return self._temp_position
        else:
            return self.position

    def set_temp_position(self, x, y, notify=True):
        self._temp_position = (x, y)
        if notify:
            self._campaign.dispatch_event(
                'on_token_temp_position_changed', self.id, self.temp_position)

    @property
    def position(self):
        return self._data.get('position', self.fragment.position)

    def set_position(self, x, y, notify=True):
        self._temp_position = None
        self._data['position'] = (x, y)
        if notify:
            self._campaign.dispatch_event('on_token_updated', self)

    @property
    def type(self):
        return self._data.get('type', self.fragment.type)

    @property
    def player(self):
        return self._data.get('player', self.fragment.player)

    @property
    def is_token(self):
        return self.type.startswith('token')

    def controlled_by(self, player):
        return player is None or player == self.player

    def move_temp(self, dx, dy):
        x, y = self.temp_position
        self.set_temp_position(x + dx, y + dy)

    def position_from_temp(self, align=False):
        x, y = self.temp_position
        if align:
            x, y = round(x), round(y)
        self.set_position(x, y)


class Page(object):
    def __init__(self, id, data, campaign):
        self._id = id
        self._data = data
        self._dispatcher = campaign
        self.tokens = []
        for token_cfg in data['tokens']:
            token = Token(token_cfg,
                          campaign.fragments[token_cfg['fragment_id']],
                          campaign)
            self.tokens.append(token)

    @property
    def veils(self):
        return self._data.get('veils', [])

    def set_veils(self, veils):
        self._data['veils'] = veils

    def toggle_veil(self, x, y):
        for veil in self.veils:
            if (veil['minx'] < x < veil['maxx'] and
                veil['miny'] < y < veil['maxy']):
                veil['covered'] = not veil['covered']
        self._dispatcher.dispatch_event(
            'on_veils_updated', self._id, self.veils)

    def find_token(self, x, y) -> Token:
        for token in self.tokens:
            if token.is_token:
                tx, ty = token.position
                if (tx <= x <= tx + token.fragment.width and
                    ty <= y <= ty + token.fragment.height):
                    return token
        return None



class Campaign(pyglet.event.EventDispatcher):

    def __init__(self, resource_provider):
        self._resource_provider = resource_provider
        with resource_provider.open('data.json') as data:
            self._data = json.load(data)
        if resource_provider.can_save:
            backup_fname = 'backups/data-{}.json'.format(
                datetime.datetime.now().strftime('%Y-%m-%dT%H%M%S'))
            resource_provider.mkdir('backups')
            resource_provider.copy_file('data.json', backup_fname)
        self.fragments = {}
        for id, frag_data in self._data['fragments'].items():
            self.fragments[id] = Fragment(frag_data, self._resource_provider, id)
        self.pages = []
        self.tokens = {}
        for (i, page_cfg) in enumerate(self._data['pages']):
            page = Page(i, page_cfg, self)
            self.pages.append(page)
            for token in page.tokens:
                self.tokens[token.id] = token

    def get_player_image(self, player):
        fragment_id = self._data['players'][player]['fragment_id']
        return self.fragments[fragment_id].image

    @property
    def players_page_idx(self):
        return self._data['players_page']

    def find_token(self, x, y) -> Token:
        for token in self.current_page.tokens:
            if token.is_token:
                tx, ty = token.position
                if (tx <= x <= tx + token.fragment.width and
                    ty <= y <= ty + token.fragment.height):
                    return token
        return None

    def set_players_page(self, i):
        self._data['players_page'] = i
        self.dispatch_event('on_page_changed', i)

    def save(self):
        with self._resource_provider.open_write('data.json') as wfile:
            saviour.save_json(self._data, wfile)

    def add_chat(self, message):
        if 'time' not in message:
            message['time'] = time.time()
        if 'chat' not in self._data:
            self._data['chat'] = []
        self._data['chat'].append(message)
        self.dispatch_event('on_new_chat', message)


Campaign.register_event_type('on_token_updated')
Campaign.register_event_type('on_token_temp_position_changed')
Campaign.register_event_type('on_page_changed')
Campaign.register_event_type('on_veils_updated')
Campaign.register_event_type('on_new_chat')
