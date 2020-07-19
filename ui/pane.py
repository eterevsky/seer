import pyglet
from pyglet import gl
from typing import Optional, Tuple, Union

from . import event
from .observable import Attribute, Observable, make_observable


class Pane(event.EventDispatcher):
    """A rectangular area in a window.

    This class dispatches mouse events related to the controlled area and draws
    its background.
    """

    coords: Attribute[Tuple[float, float, float, float]] = Attribute('coords_')
    background_color: Attribute[Tuple[int, int,
                                      int]] = Attribute('background_color_')
    mouseover: Attribute[bool] = Attribute('mouseover_')

    def __init__(self, x0: float, y0: float, x1: float, y1: float,
                 background: Union[Observable, Tuple[int, int, int]] = None):
        self.coords_: Observable[(float, float, float, float)] = Observable(
            (x0, y0, x1, y1))
        self.coords_.observe(self._prepare_background_draw)
        self.mouseover_: Observable[bool] = Observable(False)
        self.background_color_: Observable[Optional(Tuple(
            int, int, int))] = make_observable(background)
        self.background_color_.observe(self._prepare_background_draw)
        self._prepare_background_draw()

    def __str__(self):
        x0, y0, x1, y1 = self.coords
        return 'Pane({}, {}, {}, {})'.format(x0, y0, x1, y1)

    @property
    def width(self):
        return self.coords[2] - self.coords[0]

    @property
    def height(self):
        return self.coords[3] - self.coords[1]

    def _prepare_background_draw(self, *args):
        if self.background_color is None:
            self._background_shape = None
            return
        x0, y0, x1, y1 = self.coords
        self._background_shape = pyglet.shapes.Rectangle(
            x=x0, y=y0, width=(x1 - x0), height=(y1 - y0),
            color=self.background_color)

    def _draw_background(self):
        if self._background_shape is None:
            return
        self._background_shape.draw()

    @event.priority(1)
    def on_draw(self):
        self._draw_background()

    @event.priority(1)
    def on_mouse_enter(self, *args):
        # TODO: This might not work if the mouse is over the pane when it is
        # created or resized...
        self.mouseover = True

    @event.priority(1)
    def on_mouse_leave(self, *args):
        self.mouseover = False

    def contains(self, x, y):
        x0, y0, x1, y1 = self.coords
        return x0 <= x < x1 and y0 <= y < y1


Pane.register_event_type('on_draw')
Pane.register_event_type('on_mouse_drag')
Pane.register_event_type('on_mouse_enter')
Pane.register_event_type('on_mouse_leave')
Pane.register_event_type('on_mouse_press')
Pane.register_event_type('on_mouse_motion')
Pane.register_event_type('on_mouse_release')
Pane.register_event_type('on_mouse_scroll')

DUMMY_PANE = Pane(0, 0, 0, 0)
