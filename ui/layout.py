import enum
import pyglet  # type: ignore
from typing import Optional, Tuple, Union

from .event import EVENT_HANDLED, EVENT_UNHANDLED
from .observable import Attribute, Observable
from .pane import Pane
from .view import View

class RootLayout(object):
    def __init__(self, window: pyglet.window.Window, child: View = None):
        self.dragging_: Observable[bool] = Observable(False)
        self.child_pane = Pane(0, 0, window.width, window.height)
        self._child = child
        if child is not None:
            child.attach(self.child_pane)
        window.push_handlers(self)

    def __str__(self):
        content = ''
        if self.child is not None:
            content = '\n'
            for line in str(self.child).split('\n'):
                content += '  ' + line + '\n'

        return 'RootLayout({})'.format(content)

    @property
    def child(self) -> View:
        return self._child

    @child.setter
    def child(self, value: View):
        if self._child is not None:
            self._child.detach()
        self._child = value
        self._child.attach(self.child_pane)

    def on_draw(self):
        self.child_pane.dispatch_event('on_draw')

    def on_mouse_enter(self, x, y):
        self.child_pane.mouse_pos = (x, y)

    def on_mouse_leave(self, x, y):
        self.child_pane.mouse_pos = None

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.child_pane.mouse_pos = (x, y)
        self.child_pane.dispatch_event(
            'on_mouse_drag', x, y, dx, dy, buttons, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        self.child_pane.mouse_pos = (x, y)

    def on_mouse_press(self, *args):
        self.child_pane.dispatch_event('on_mouse_press', *args)

    def on_mouse_release(self, *args):
        self.child_pane.dispatch_event('on_mouse_release', *args)

    def on_mouse_scroll(self, *args):
        self.child_pane.dispatch_event('on_mouse_scroll', *args)

    def on_resize(self, width, height):
        self.child_pane.coords = (0, 0, width, height)


class Orientation(enum.Enum):
    HORIZONTAL = 1
    VERTICAL = 2


class StackLayout(View):
    def __init__(self, orientation: Orientation, *children, **kwargs):
        super().__init__(**kwargs)

        self.orientation = orientation
        self.children = children
        self.mouseover_pane = None
        self._dragging_pane = None
        self._dragging_button = 0

        if not self.min_width_set():
            if self.orientation == Orientation.HORIZONTAL:
                min_width = sum(c.min_width for c in self.children)
            else:
                min_width = max(c.min_width for c in self.children)
            self.set_min_width(min_width)

        if not self.min_height_set():
            if self.orientation == Orientation.VERTICAL:
                min_height = sum(c.min_height for c in self.children)
            else:
                min_height = max(c.min_height for c in self.children)
            self.set_min_height(min_height)

        if not self.flex_width_set():
            self.set_flex_width(any(c.flex_width for c in self.children))

        if not self.flex_height_set():
            self.set_flex_width(any(c.flex_height for c in self.children))

    def __str__(self):
        content = ''
        for child in self.children:
            for line in str(child).split('\n'):
                content += '\n  ' + line
            content += ','
        content += '\n'

        return '{}[{}]({})'.format(self.__class__.__name__, self.pane, content)

    def attach(self, pane: Pane):
        super().attach(pane)
        x0, y0, x1, y1 = self.pane.x0, self.pane.y0, self.pane.x1, self.pane.y1
        if self.orientation == Orientation.HORIZONTAL:
            y0 = y1
        else:
            x1 = x0
        for child in self.children:
            child_pane = Pane(pane.window, x0, y0, x1, y1)
            child.attach(child_pane)
            child_pane.push_handlers(self.on_content_resize)

    def detach(self):
        super().detach()
        for child in self.children:
            child.pane.remove_handlers(self)
            child.detach()

    def _find_child_pane(self, x, y) -> Pane:
        """Returns the child contining (x, y) or None."""
        if (self.mouseover_pane is not None
                and self.mouseover_pane.contains(x, y)):
            return self.mouseover_pane
        for child in self.children:
            if child.pane.contains(x, y):
                return child.pane
        return None

    def on_draw(self):
        for child in self.children:
            child.pane.dispatch_event('on_draw')

    def on_mouse_enter(self, x, y):
        self.mouseover_pane = self._find_child_pane(x, y)
        if self.mouseover_pane:
            return self.mouseover_pane.dispatch_event('on_mouse_enter', x, y)

    def on_mouse_leave(self, x, y):
        if self.mouseover_pane:
            pane = self.mouseover_pane
            self.mouseover_pane = None
            return pane.dispatch_event('on_mouse_leave', x, y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._dragging_pane is None:
            self._dragging_button = buttons
            self._dragging_pane = self._find_child_pane(x, y)

        if self._dragging_pane:
            self._dragging_pane.dispatch_event('on_mouse_drag', x, y, dx, dy,
                                               buttons, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        pane = self._find_child_pane(x, y)
        if pane is not self.mouseover_pane:
            if self.mouseover_pane is not None:
                self.mouseover_pane.dispatch_event('on_mouse_leave', x, y)
            self.mouseover_pane = pane
            if pane is not None:
                pane.dispatch_event('on_mouse_enter', x, y)
        if pane is not None:
            return pane.dispatch_event('on_mouse_motion', x, y, dx, dy)

    def on_mouse_press(self, x, y, button, modifiers):
        pane = self._find_child_pane(x, y)
        if pane:
            return pane.dispatch_event('on_mouse_press', x, y, button,
                                       modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        if button & self._dragging_button:
            self._dragging_pane = None
            self._dragging_button = 0
        pane = self._find_child_pane(x, y)
        if pane:
            return pane.dispatch_event('on_mouse_release', x, y, button,
                                       modifiers)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        pane = self._find_child_pane(x, y)
        if pane:
            return pane.dispatch_event('on_mouse_scroll', x, y, scroll_x,
                                       scroll_y)

    def on_dims_change(self, *args):
        self._resize()

    def on_content_resize(self):
        print(self, 'on_content_resize')
        self._resize(debug=True)

    def _resize(self, debug=False):
        if debug:
            for c in self.children:
                print(c.min_width)

        if self.orientation == Orientation.HORIZONTAL:
            dim = self.pane.width
            min_dims = [child.pane.min_width for child in self.children]
            flexes = [child.pane.flex_width for child in self.children]
            offset = self.pane.x0
        elif self.orientation == Orientation.VERTICAL:
            dim = self.pane.height
            min_dims = [child.min_height for child in self.children]
            flexes = [child.pane.flex_height for child in self.children]
            offset = self.pane.y1
        else:
            raise AttributeError()

        count_flex = sum(flexes)
        min_dim = sum(min_dims)
        extra_dim = (dim - min_dim) / max(count_flex, 1)

        if debug:
            print('min_dims', min_dims)
            print('flexes', flexes)
            for c in self.children:
                print(c.min_width)

        for child, min_dim, flex in zip(self.children, min_dims, flexes):
            pane = child.pane

            if self.orientation == Orientation.HORIZONTAL:
                if extra_dim <= 0 or not flex:
                    next_offset = min(offset + min_dim, self.pane.x1)
                else:
                    next_offset = offset + min_dim + extra_dim
                pane.change_dims(x0=offset, x1=next_offset, y0=self.pane.y0,
                                 y1=self.pane.y1)
            else:
                if extra_dim <= 0 or not flex:
                    next_offset = max(offset - min_dim, self.pane.y0)
                else:
                    next_offset = offset - min_dim - extra_dim
                pane.change_dims(x0=self.pane.x0, x1=self.pane.x1,
                                 y0=next_offset, y1=offset)

            offset = next_offset


class HStackLayout(StackLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(Orientation.HORIZONTAL, *args, **kwargs)


class VStackLayout(StackLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(Orientation.VERTICAL, *args, **kwargs)


class LayersLayout(View):
    def __init__(self, *children, **kwargs):
        super().__init__(**kwargs)

        self.children = children

        if not self.min_width_set():
            self.set_min_width(max(c.min_width for c in self.children))
        if not self.min_height_set():
            self.set_min_height(max(c.min_height for c in self.children))
        if not self.flex_width_set():
            self.set_flex_width(any(c.flex_width for c in self.children))
        if not self.flex_height_set():
            self.set_flex_width(any(c.flex_height for c in self.children))

    def __str__(self):
        content = ''
        for child in self.children:
            for line in str(child).split('\n'):
                content += '\n  ' + line
            content += ','
        content += '\n'

        return '{}[{}]({})'.format(self.__class__.__name__, self.pane, content)

    def attach(self, pane: Pane):
        super().attach(pane)
        x0, y0, x1, y1 = self.pane.x0, self.pane.y0, self.pane.x1, self.pane.y1
        for child in self.children:
            child_pane = Pane(pane.window, x0, y0, x1, y1)
            child.attach(child_pane)
            pane.push_handlers(self.on_content_resize)

    def detach(self):
        super().detach()
        for child in self.children:
            child.pane.remove_handlers(self)
            child.detach()

    def on_draw(self):
        for child in self.children:
            child.pane.dispatch_event('on_draw')

    def on_mouse_enter(self, x, y):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_enter', x, y) is
                    EVENT_HANDLED):
                break

    def on_mouse_leave(self, x, y):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_leave', x, y) is
                    EVENT_HANDLED):
                break

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_drag', x, y, dx, dy,
                                          buttons, modifiers) is
                    EVENT_HANDLED):
                break

    def on_mouse_motion(self, x, y, dx, dy):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_motion', x, y, dx, dy) is
                    EVENT_HANDLED):
                break

    def on_mouse_press(self, x, y, button, modifiers):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_press', x, y, button,
                                          modifiers) is EVENT_HANDLED):
                break

    def on_mouse_release(self, x, y, button, modifiers):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_release', x, y, button,
                                          modifiers) is EVENT_HANDLED):
                break

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        for child in reversed(self.children):
            if (child.pane.dispatch_event('on_mouse_scroll', x, y, scroll_x,
                                          scroll_y) is EVENT_HANDLED):
                break

    def on_dims_change(self, *args):
        self._resize()

    def on_content_resize(self):
        self._resize()

    def _resize(self):
        for child in self.children:
            child.pane.change_dims(x0=self.pane.x0, x1=self.pane.x1,
                                   y0=self.pane.y0, y1=self.pane.y1)


class Spacer(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
