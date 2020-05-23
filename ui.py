import enum
import pyglet
from typing import List, Union


class Pane(pyglet.event.EventDispatcher):
    """A rectangular area in a window.

    This class manages mouse events related to the controlled area, and
    negotiates with the owning layout its size and location in the window.
    """

    def __init__(self, content_width=None, content_height=None, background=None):
        self.content_width = content_width
        self.content_height = content_height
        self.offset_x = None
        self.offset_y = None
        self.width = None
        self.height = None
        self.background = background

    def _prepare_draw(self):
        if self.background is None or self.width is None:
            return

        x0, y0 = self.offset_x, self.offset_y
        x1, y1 = x0 + self.width, y0 + self.height

        self._triangles = [
            x0, y0,  x1, y0,  x1, y1,
            x0, y0,  x1, y1,  x0, y1
        ]

        self._colors = self.background * 6

    def on_draw(self):
        if self.background is None:
            return

        pyglet.graphics.draw(
            6, pyglet.gl.GL_TRIANGLES,
            ('v2f', self._triangles),
            ('c3B', self._colors))

    def on_resize(self, width, height, offset_x, offset_y):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.width = width
        self.height = height
        self._prepare_draw()

    def contains(self, x, y):
        return (self.offset_x <= x < self.offset_x + self.width and
                self.offset_y <= y < self.offset_y + self.height)


Pane.register_event_type('on_draw')
Pane.register_event_type('on_mouse_enter')
Pane.register_event_type('on_mouse_leave')
Pane.register_event_type('on_mouse_press')
Pane.register_event_type('on_mouse_motion')
Pane.register_event_type('on_mouse_release')
Pane.register_event_type('on_mouse_scroll')
Pane.register_event_type('on_resize')


class Orientation(enum.Enum):
    HORIZONTAL = 1
    VERTICAL = 2


class StackLayout(object):
    def __init__(self,
                 orientation: Orientation,
                 parent: Union[pyglet.window.Window, Pane],
                 children: List[Pane]):
        self.orientation = orientation
        self.parent = parent
        self.children = children
        self._resize()
        self.parent.push_handlers(self)
        self.mouseover_child = None

    @property
    def offset_x(self):
        return getattr(self.parent, 'offset_x', 0)

    @property
    def offset_y(self):
        return getattr(self.parent, 'offset_y', 0)

    def on_draw(self):
        for child in self.children:
            child.dispatch_event('on_draw')

    def on_mouse_enter(self, x, y):
        self.mouseover_child = self._find_child(x, y)
        if self.mouseover_child:
            return self.mouseover_child.dispatch_event('on_mouse_enter', x, y)

    def on_mouse_leave(self, x, y):
        if self.mouseover_child:
            child = self.mouseover_child
            self.mouseover_child = None
            return child.dispatch_event('on_mouse_leave', x, y)

    def on_mouse_motion(self, x, y, dx, dy):
        child = self._find_child(x, y)
        if child is not self.mouseover_child:
            if self.mouseover_child is not None:
                self.mouseover_child.dispatch_event('on_mouse_leave', x, y)
            self.mouseover_child = child
            child.dispatch_event('on_mouse_enter', x, y)
        if child:
            return child.dispatch_event('on_mouse_motion', x, y, dx, dy)

    def on_mouse_press(self, x, y, button, modifiers):
        child = self._find_child(x, y)
        if child:
            return child.dispatch_event('on_mouse_press', x, y, button, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        child = self._find_child(x, y)
        if child:
            return child.dispatch_event('on_mouse_release', x, y, button, modifiers)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        child = self._find_child(x, y)
        if child:
            return child.dispatch_event('on_mouse_scroll', x, y, scroll_x, scroll_y)

    def on_resize(self, width, height, offset_x=0, offset_y=0):
        self._resize()

    def _resize(self):
        if self.orientation == Orientation.HORIZONTAL:
            dim = self.parent.width
            content_dims = [child.content_width for child in self.children]
            offset = self.offset_x
        elif self.orientation == Orientation.VERTICAL:
            dim = self.parent.height
            content_dims = [child.content_height for child in self.children]
            offset = self.offset_y
        else:
            raise AttributeError()

        count_greedy = sum(d is None for d in content_dims)
        content_dim = sum(d or 0 for d in content_dims)
        extra_dim = max(dim - content_dim, 0)

        print('count_greedy', count_greedy)
        print('content_dim', content_dim)
        print('extra_dim', extra_dim)
        print('content_dims', content_dims)

        for child, dim in zip(self.children, content_dims):
            print('offset', offset)
            if dim is None:
                d = extra_dim / count_greedy
            else:
                d = dim
            if self.orientation == Orientation.HORIZONTAL:
                child.dispatch_event(
                    'on_resize', d, self.parent.height, offset, self.offset_y)
            else:
                child.dispatch_event(
                    'on_resize', self.parent.width, d, self.offset_x, offset)
            offset += d

    def _find_child(self, x, y):
        """Returns the child contining (x, y) or None."""
        if (self.mouseover_child is not None and
            self.mouseover_child.contains(x,y)):
            return self.mouseover_child
        for child in self.children:
            if child.contains(x, y):
                return child
        return None