class State(object):
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
            self.current_char = campaign.players[player].default_character
        else:
            self.current_char = None

    @property
    def current_page_idx(self):
        if self._current_page_idx is None:
            return self.campaign.players_page_idx
        else:
            return self._current_page_idx

    @property
    def is_master(self):
        return self.player is None

    def get_current_char(self):
        return self.current_char

    def get_current_char_name(self):
        if self.current_char is not None:
            return self.current_char.name
        else:
            return ''

    def get_current_char_image(self):
        if self.current_char is not None:
            return self.current_char.fragment.image
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
