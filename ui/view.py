from .pane import Pane, DUMMY_PANE
from ui import event

class View(object):
    def __init__(self, min_width=None, min_height=None, flex_width=None,
                 flex_height=None, background=None, get_hidden=None):
        self.pane = DUMMY_PANE
        self._min_width = min_width
        self._min_height = min_height
        self._flex_width = flex_width
        self._flex_height = flex_height
        self.background = background
        self.get_hidden = get_hidden

    def __str__(self):
        return '{}[{}]{}'.format(self.__class__.__name__, self.pane,
                                 '[hidden]' if self.hidden else '')

    @property
    def hidden(self):
        return self.get_hidden is not None and self.get_hidden()

    @property
    def min_width(self):
        if self.hidden or self._min_width is None:
            return 0
        else:
            return self._min_width

    def min_width_set(self):
        return self._min_width is not None

    def set_min_width(self, value):
        self._min_width = value
        self._update_dims()
        return self

    @property
    def min_height(self):
        if self.hidden or self._min_height is None:
            return 0
        else:
            return self._min_height

    def min_height_set(self):
        return self._min_height is not None

    def set_min_height(self, value):
        self._min_height = value
        self._update_dims()
        return self

    @property
    def flex_width(self):
        return not self.hidden and (self._flex_width is None
                                    or self._flex_width)

    def flex_width_set(self):
        return self._flex_width is not None

    def set_flex_width(self, value: bool):
        self._flex_width = value
        self._update_dims()
        return self

    @property
    def flex_height(self):
        return not self.hidden and (self._flex_height is None
                                    or self._flex_height)

    def flex_height_set(self):
        return self._flex_height is not None

    def set_flex_height(self, value: bool):
        self._flex_height = value
        self._update_dims()
        return self

    def set_background(self, value):
        self.background = value
        self.pane.background = value
        return self

    def attach(self, pane: Pane):
        self.pane.remove_handlers(self)
        self.pane = pane
        self.pane.push_handlers(self)
        self.pane.push_handlers(on_draw=self.on_draw_check_hidden)
        self.pane.background = self.background
        self._update_dims()

    def detach(self):
        self.pane.remove_handlers(self)
        self.pane = DUMMY_PANE

    def _update_dims(self):
        print(self, '_update_dims', self.min_width)
        self.pane.change_content_dims(self.min_width, self.min_height,
                                      self.flex_width, self.flex_height)

    def on_mouse_enter(self, *args):
        self.pane.window.set_mouse_cursor(None)

    @event.priority(1)
    def on_draw_check_hidden(self):
        if self.hidden:
            return event.EVENT_HANDLED
