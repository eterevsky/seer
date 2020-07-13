import pyglet
from pyglet import gl

from ui import event


class Pane(event.EventDispatcher):
    """A rectangular area in a window.

    This class dispatches mouse events related to the controlled area and draws
    its background.
    """
    def __init__(self, window, x0, y0, x1, y1, background=None):
        self.window = window
        self.x0, self.y0 = x0, y0
        self.x1, self.y1 = x1, y1
        self.min_width = 0
        self.min_height = 0
        self.flex_width = True
        self.flex_height = True
        self.mouseover = False
        self._background = background
        self._prepare_background_draw()

    def __str__(self):
        return 'Pane({}, {}, {}, {})'.format(self.x0, self.y0, self.x1,
                                             self.y1)

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def background(self):
        return self._background

    @background.setter
    def background(self, value):
        self._background = value
        self._prepare_background_draw()

    def update_layout(self):
        self.dispatch_event('on_resize', self.width, self.height, self.x0,
                            self.y0)
        self.dispatch_event('on_dims_change', self.x0, self.y0, self.x1,
                            self.y0)

    def change_dims(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0
        self.x1, self.y1 = x1, y1
        self._prepare_background_draw()
        self.dispatch_event('on_resize', self.width, self.height, self.x0,
                            self.y0)
        self.dispatch_event('on_dims_change', self.x0, self.y0, self.x1,
                            self.y0)

    def change_content_dims(self, min_width=0, min_height=0, flex_width=True,
                            flex_height=True):
        self.min_width = min_width
        self.min_height = min_height
        self.flex_width = flex_width
        self.flex_height = flex_height
        self.dispatch_event('on_content_resize')

    def _prepare_background_draw(self):
        if self._background is None:
            return
        self._triangles = [
            self.x0, self.y0, self.x1, self.y0, self.x1, self.y1,
            self.x0, self.y0, self.x1, self.y1, self.x0, self.y1
        ]  # yapf: disable
        self._colors = self._background * 6

    def _draw_background(self):
        if self._background is None:
            return

        # print('_draw_bakground', self._triangles, self._colors)
        pyglet.graphics.draw(6, pyglet.gl.GL_TRIANGLES,
                             ('v2f', self._triangles), ('c3B', self._colors))

    @event.priority(1)
    def on_draw(self):
        self._draw_background()

    @event.priority(1)
    def on_dim_change(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self._prepare_background_draw()

    @event.priority(1)
    def on_mouse_enter(self, *args):
        # This might not work if the mouse is over the pane when it is created
        # or resized, but oh well...
        self.mouseover = True

    @event.priority(1)
    def on_mouse_leave(self, *args):
        self.mouseover = False

    def contains(self, x, y):
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1


Pane.register_event_type('on_draw')
Pane.register_event_type('on_mouse_drag')
Pane.register_event_type('on_mouse_enter')
Pane.register_event_type('on_mouse_leave')
Pane.register_event_type('on_mouse_press')
Pane.register_event_type('on_mouse_motion')
Pane.register_event_type('on_mouse_release')
Pane.register_event_type('on_mouse_scroll')
Pane.register_event_type('on_dims_change')
Pane.register_event_type('on_resize')
Pane.register_event_type('on_content_resize')

DUMMY_PANE = Pane(None, 0, 0, 0, 0)
