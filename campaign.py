"""The representation of the game state."""

import datetime
import json
import os.path
import pyglet


class Fragment(object):
    """A sprite representing a token or a map tile.

    May contain the default values for controlling player and position.
    """

    def __init__(self, data, provider, id):
        self.id = id
        self._data = data
        fname = os.path.basename(data['path'])
        with provider.open(data['path']) as file:
            img = pyglet.image.load(fname, file=file)
        self._img_width = img.width
        self._img_height = img.height
        self.sprite = pyglet.sprite.Sprite(img=img, subpixel=True)

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
            return self.sprite.width / self._data['resolution']

    @property
    def height(self) -> float:
        if 'height' in self._data:
            return self._data['height']
        else:
            return self._img_height / self._data['resolution']

    @property
    def size(self) -> (float, float):
        return self.width, self.height

    @property
    def resolution(self) -> float:
        if 'resolution' in self._data:
            return self._data['resolution']
        else:
            return self._img_width / self.width


class Token(object):
    """A token or a map tile added to a page.

    Contains the fragment that is drawn with its position. A single fragment
    can be added multiple times to one or more maps. Each such instance has
    the same `Fragment`, but separate Token.
    """

    def __init__(self, data, fragment, dispatcher):
        self._data = data
        self.fragment = fragment
        self._dispatcher = dispatcher

    def _update(self):
        self._dispatcher.dispatch_event('on_token_updated', self)

    def update_data(self, data):
        self._data = data

    @property
    def position(self):
        return self._data.get('position', self.fragment.position)

    @property
    def type(self):
        return self._data.get('type', self.fragment.type)

    @property
    def player(self):
        return self._data.get('player', self.fragment.player)

    @property
    def is_token(self):
        return self.type.startswith('token')

    def set_position(self, x, y):
        self._data['position'] = (x, y)
        self._update()

    @property
    def id(self):
        return self._data['id']

    def controlled_by(self, player):
        return player is None or player == self.player

    def move(self, dx, dy):
        x, y = self._data['position']
        self._data['position'] = (x + dx, y + dy)
        self._update()

    def align_to_grid(self):
        x, y = self._data['position']
        x, y = round(x), round(y)
        self._data['position'] = (x, y)
        self._update()


class Page(object):
    def __init__(self, data, campaign):
        self._data = data
        self.tokens = []
        for token_cfg in data['tokens']:
            token = Token(token_cfg,
                          campaign.fragments[token_cfg['fragment_id']],
                          campaign)
            self.tokens.append(token)


class Campaign(pyglet.event.EventDispatcher):

    def __init__(self, resource_provider, player):
        self.register_event_type('on_token_updated')
        self.register_event_type('on_page_changed')
        self._player = player
        self._resource_provider = resource_provider
        with resource_provider.open('data.json') as data:
            self._data = json.load(data)
        if resource_provider.can_save:
            backup_fname = 'backups/data-{}.json'.format(
                datetime.datetime.now().strftime('%Y-%m-%dT%H%M%S'))
            resource_provider.copy_file('data.json', backup_fname)
        self.fragments = {}
        for id, frag_data in self._data['fragments'].items():
            self.fragments[id] = Fragment(frag_data, self._resource_provider, id)
        self.pages = []
        self.tokens = {}
        for page_cfg in self._data['pages']:
            page = Page(page_cfg, self)
            self.pages.append(page)
            for token in page.tokens:
                self.tokens[token.id] = token

    @property
    def master_page(self):
        return self._data['master_page']

    @property
    def current_page(self):
        if self._player is None:
            idx = self._data['master_page']
        else:
            idx = self._data['players_page']
        return self.pages[idx]

    def find_token(self, x, y) -> Token:
        for token in self.current_page.tokens:
            if token.is_token:
                tx, ty = token.position
                if (tx <= x <= tx + token.fragment.width and
                    ty <= y <= ty + token.fragment.height):
                    return token
        return None

    def next_page(self):
        if (self._player is None and
            self._data['master_page'] + 1 < len(self.pages)):
            self._data['master_page'] += 1

    def prev_page(self):
        if self._player is None and self._data['master_page'] > 0:
            self._data['master_page'] -= 1

    def set_players_page(self, i):
        self._data['players_page'] = i
        self.dispatch_event('on_page_changed', i)

    def save(self):
        with self._resource_provider.open_write('data.json') as wfile:
            json.dump(self._data, wfile, indent=2, sort_keys=True)
