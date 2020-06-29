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

    def __init__(self, id: str, data: dict, provider):
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


class Character(object):
    """Represents any character, NPC or monster."""

    def __init__(self, id: str, data: dict, campaign):
        self.id = id
        self._data = data
        self.fragment = campaign.fragments[self._data['fragment']]

    def controlled_by(self, player):
        return self._data.get('player', None) == player

    @property
    def name(self):
        return self._data['name']

    @property
    def hp(self):
        return self._data['hp']

    @property
    def maxhp(self):
        return self._data['maxhp']


class Token(object):
    """A token or a map tile added to a page.

    Contains the fragment that is drawn with its position. A single fragment
    can be added multiple times to one or more maps. Each such instance has
    the same `Fragment`, but separate Token.
    """

    def __init__(self, data, campaign):
        self._data = data
        self._campaign = campaign
        assert 'fragment' in self._data or 'character' in self._data
        if 'fragment' in self._data:
            self._fragment = self._campaign.fragments[self._data['fragment']]
        else:
            self._fragment = None
        if 'character' in self._data:
            self.character = self._campaign.characters[self._data['character']]
        else:
            self.character = None
        self._temp_position = None

    def update_data(self, data, notify=False):
        self._data = data
        self._temp_position = None
        if notify:
            self._campaign.dispatch_event('on_token_updated', self)

    @property
    def is_character(self) -> bool:
        return 'character' in self._data

    @property
    def fragment(self):
        if self._fragment is not None:
            return self._fragment
        else:
            return self.character.fragment

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
        return self._data['position']

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
        return (player is None or
                (self.character is not None and
                 self.character.controlled_by(player)))

    def move_temp(self, dx, dy):
        x, y = self.temp_position
        self.set_temp_position(x + dx, y + dy)

    def position_from_temp(self, align=False):
        x, y = self.temp_position
        if align:
            x, y = round(x), round(y)
        self.set_position(x, y)


class Page(object):
    def __init__(self, id: str, data: dict, campaign):
        self.id = id
        self._data = data
        self._campaign = campaign
        self.tokens = []
        for token_data in data['tokens']:
            token = Token(token_data, campaign)
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
        self._campaign.dispatch_event('on_veils_updated', self.id, self.veils)

    def find_token(self, x, y) -> Token:
        for token in self.tokens:
            if token.is_token:
                tx, ty = token.position
                if (tx <= x <= tx + token.fragment.width and
                    ty <= y <= ty + token.fragment.height):
                    return token
        return None


class Player(object):
    def __init__(self, name, data, campaign):
        self.name = name
        self._data = data
        self.default_character = campaign.characters[
            self._data['default_character']]


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
            self.fragments[id] = Fragment(id, frag_data, self._resource_provider)

        self.characters = {}
        for id, char_data in self._data['characters'].items():
            self.characters[id] = Character(id, char_data, self)

        self.pages = []
        self.tokens = {}
        for (i, page_data) in enumerate(self._data['pages']):
            page = Page(i, page_data, self)
            self.pages.append(page)
            for token in page.tokens:
                self.tokens[token.id] = token

        self.players = {}
        for player, player_data in self._data['players'].items():
            self.players[player] = Player(player, player_data, self)

    @property
    def players_page_idx(self):
        return self._data['players_page']

    @players_page_idx.setter
    def players_page_idx(self, i):
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
