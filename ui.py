import enum
import functools
import pyglet
from pyglet.window import key
from typing import List, Union


class Pane(pyglet.event.EventDispatcher):
    """A rectangular area in a window.

    This class manages mouse events related to the controlled area, and
    negotiates with the owning layout its size and location in the window.
    """

    def __init__(self, content=None, content_width=None, content_height=None,
                 background=None):
        self.content_width = content_width
        self.content_height = content_height
        self.offset_x = 0
        self.offset_y = 0
        self.width = 0
        self.height = 0
        self.background = background

    @property
    def materialized(self):
        return self.width is not None

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

    def draw_background(self):
        if self.background is None:
            return

        pyglet.graphics.draw(
            6, pyglet.gl.GL_TRIANGLES,
            ('v2f', self._triangles),
            ('c3B', self._colors))

    @pyglet.event.intercept
    def on_draw(self):
        self.draw_background()

    @pyglet.event.intercept
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
Pane.register_event_type('on_mouse_drag')
Pane.register_event_type('on_mouse_enter')
Pane.register_event_type('on_mouse_leave')
Pane.register_event_type('on_mouse_press')
Pane.register_event_type('on_mouse_motion')
Pane.register_event_type('on_mouse_release')
Pane.register_event_type('on_mouse_scroll')
Pane.register_event_type('on_resize')
Pane.register_event_type('on_content_resize')


class Controller(object):
    def __init__(self,
            pane: Union[pyglet.window.Window, Pane] = None, **kwargs):
        if pane is None:
            self.pane = Pane(**kwargs)
        else:
            self.pane = pane
        self.pane.content = self


class Orientation(enum.Enum):
    HORIZONTAL = 1
    VERTICAL = 2


class StackLayout(Controller):
    def __init__(self,
                 orientation: Orientation,
                 parent: Union[pyglet.window.Window, Pane] = None,
                 **kwargs):
        super().__init__(parent, **kwargs)
        self.orientation = orientation
        self.children = []
        self.pane.push_handlers(self)
        self.mouseover_child = None
        self._dragging_child = None
        self._dragging_button = 0

    @property
    def offset_x(self):
        return getattr(self.pane, 'offset_x', 0)

    @property
    def offset_y(self):
        return getattr(self.pane, 'offset_y', 0)

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

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._dragging_child is None:
            self._dragging_button = buttons
            self._dragging_child = self._find_child(x, y)

        self._dragging_child.dispatch_event(
            'on_mouse_drag', x, y, dx, dy, buttons, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        child = self._find_child(x, y)
        if child is not self.mouseover_child:
            if self.mouseover_child is not None:
                self.mouseover_child.dispatch_event('on_mouse_leave', x, y)
            self.mouseover_child = child
            if child is not None:
                child.dispatch_event('on_mouse_enter', x, y)
        if child is not None:
            return child.dispatch_event('on_mouse_motion', x, y, dx, dy)

    def on_mouse_press(self, x, y, button, modifiers):
        child = self._find_child(x, y)
        if child:
            return child.dispatch_event('on_mouse_press', x, y, button, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        if button & self._dragging_button:
            self._dragging_child = None
            self._dragging_button = 0
        child = self._find_child(x, y)
        if child:
            return child.dispatch_event('on_mouse_release', x, y, button, modifiers)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        child = self._find_child(x, y)
        if child:
            return child.dispatch_event('on_mouse_scroll', x, y, scroll_x, scroll_y)

    def on_resize(self, width, height, offset_x=0, offset_y=0):
        self._resize()

    def add_child(self, child: Union[Pane, Controller]) -> None:
        if isinstance(child, Pane):
            self.children.append(child)
        else:
            self.children.append(child.pane)
        self._resize()

    def _resize(self):
        if self.orientation == Orientation.HORIZONTAL:
            dim = self.pane.width
            content_dims = [child.content_width for child in self.children]
            offset = self.offset_x
        elif self.orientation == Orientation.VERTICAL:
            dim = self.pane.height
            content_dims = [child.content_height for child in self.children]
            offset = self.offset_y + dim
        else:
            raise AttributeError()

        count_greedy = sum(d is None for d in content_dims)
        content_dim = sum(d or 0 for d in content_dims)
        extra_dim = max(dim - content_dim, 0)

        for child, dim in zip(self.children, content_dims):
            if dim is None:
                d = extra_dim / count_greedy
            else:
                d = dim
            if self.orientation == Orientation.HORIZONTAL:
                child.dispatch_event(
                    'on_resize', d, self.pane.height, offset, self.offset_y)
                offset += d
            else:
                offset -= d
                child.dispatch_event(
                    'on_resize', self.pane.width, d, self.offset_x, offset)

    def _find_child(self, x, y):
        """Returns the child contining (x, y) or None."""
        if (self.mouseover_child is not None and
            self.mouseover_child.contains(x,y)):
            return self.mouseover_child
        for child in self.children:
            if child.contains(x, y):
                return child
        return None


class TextInput(Controller):
    def __init__(self, content_width=100, content_height=100, background=None):
        super().__init__(content_width=content_width,
                         content_height=content_height,
                         background=background)
        self.pane.push_handlers(self)
        self.pane.content = self
        self.document = pyglet.text.document.UnformattedDocument('')
        self.layout = pyglet.text.layout.IncrementalTextLayout(
            self.document, content_width, content_height, multiline=True,
            wrap_lines=True)
        self.caret = pyglet.text.caret.Caret(self.layout)
        self.caret.visible = False

    def on_resize(self, width, height, offset_x, offset_y):
        print('on_resize', width, height, offset_x, offset_y)
        if width <= 0 or height <= 0:
            self.caret.visible = False
            return
        self.caret.visible = True
        self.layout.width = width
        self.layout.height = height
        self.layout.x = offset_x
        self.layout.y = offset_y

    def on_draw(self):
        self.layout.draw()

    def on_return(self):
        pass


class FocusManager(object):
    def __init__(self, window):
        self.window = window
        window.push_handlers(self)
        self._inputs = []
        self._focus = None
        self._text_cursor = window.get_system_mouse_cursor('text')
        print(self._text_cursor)

    def add_input(self, controller):
        self._inputs.append(controller)

    def _find_input(self, x, y):
        if self._focus is not None and self._focus.pane.contains(x, y):
            return self._focus
        for controller in self._inputs:
            if controller.pane.contains(x, y):
                return controller
        return None

    def on_mouse_press(self, x, y, button, modifiers):
        target = self._find_input(x, y)
        if target is not self._focus and self._focus is not None:
            print('switch')
            self._focus.caret.visible = False
        self._focus = target
        if target is not None:
            self._focus.caret.visible = True
            return target.caret.on_mouse_press(x, y, button, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        target = self._find_input(x, y)
        print('on_mouse_motion', target)
        self.window.set_mouse_cursor(
            None if target is None else self._text_cursor)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._focus:
            return self._focus.caret.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_text(self, text):
        if self._focus:
            return self._focus.caret.on_text(text)

    def on_text_motion(self, motion):
        if self._focus:
            return self._focus.caret.on_text_motion(motion)

    def on_text_motion_select(self, motion):
        if self._focus:
            return self._focus.caret.on_text_motion_select(motion)

    def on_key_press(self, symbol, modifiers):
        if not self._focus:
            return pyglet.event.EVENT_UNHANDLED
        if symbol == key.ESCAPE:
            self._focus = None
            self._focus.caret.visible = False
            return pyglet.event.EVENT_HANDLED
        if symbol == key.ENTER:
            return self._focus.on_return()

        if key.SPACE <= symbol <= key.ASCIITILDE or symbol in (
            key.UP, key.RIGHT, key.DOWN, key.LEFT,
            key.BACKSPACE, key.DELETE):
            return pyglet.event.EVENT_HANDLED
        return pyglet.event.EVENT_UNHANDLED
