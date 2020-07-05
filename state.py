import pyglet

class State(pyglet.event.EventDispatcher):
    """Transient state of the game client.

    This client contains game client state that is a) not shared between the
    clients, b) not saved upon exit. All the permanent state is contained in
    Campaign class.
    """
    def __init__(self, campaign, player):
        self.campaign = campaign
        self.player = player

        self.dragged_token = None
        self._current_page_idx = None
        if self.player:
            self._current_char = campaign.players[player].default_character
        else:
            self._current_char = None

    @property
    def current_page_idx(self):
        if self._current_page_idx is None:
            return self.campaign.players_page_idx
        else:
            return self._current_page_idx

    @property
    def is_master(self):
        return self.player is None

    @property
    def current_char(self):
        return self._current_char

    @current_char.setter
    def current_char(self, value):
        self._current_char = value
        self.dispatch_event('on_current_char_changed')

    def no_selected_char(self):
        return self._current_char is None

    def get_current_char(self):
        return self._current_char

    def get_current_char_name(self):
        if self._current_char is not None:
            return self._current_char.name
        else:
            return ''

    def get_current_char_image(self):
        if self._current_char is not None:
            return self._current_char.fragment.image
        else:
            return None

    @property
    def current_page(self):
        return self.campaign.pages[self.current_page_idx]

    def next_page(self):
        if (self.is_master and
            self.current_page_idx + 1 < len(self.campaign.pages)):
            self._current_page_idx = self.current_page_idx + 1

    def prev_page(self):
        if self.is_master and self.current_page_idx > 0:
            self._current_page_idx = self.current_page_idx - 1


State.register_event_type('on_current_char_changed')
