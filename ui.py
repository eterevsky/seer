import enum
import event
import pyglet
from pyglet import gl
from pyglet.window import key
from pyglet.event import EVENT_HANDLED
from typing import List, Union


class Pane(event.EventDispatcher):
    """A rectangular area in a window.

    This class dispatches mouse events related to the controlled area and draws
    its background.
    """
    def __init__(self, x0, y0, x1, y1, background=None):
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
            self.x0, self.y0, self.x1, self.y0, self.x1, self.y1, self.x0,
            self.y0, self.x1, self.y1, self.x0, self.y1
        ]
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

DUMMY_PANE = Pane(0, 0, 0, 0)


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
        self.pane.background = self.background
        self._update_dims()

    def detach(self):
        self.pane.remove_handlers(self)
        self.pane = DUMMY_PANE

    def _update_dims(self):
        self.pane.change_content_dims(self.min_width, self.min_height,
                                      self.flex_width, self.flex_height)


class RootLayout(object):
    def __init__(self, window: pyglet.window.Window, child: View = None,
                 background=None):
        self.child_pane = Pane(0, 0, window.width, window.height,
                               background=background)
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

    def update_layout(self):
        self.child_pane.update_layout()

    def on_draw(self):
        self.child_pane.dispatch_event('on_draw')

    def on_mouse_enter(self, x, y):
        self.child_pane.dispatch_event('on_mouse_enter', x, y)

    def on_mouse_leave(self, x, y):
        self.child_pane.dispatch_event('on_mouse_leave', x, y)

    def on_mouse_drag(self, *args):
        self.child_pane.dispatch_event('on_mouse_drag', *args)

    def on_mouse_motion(self, *args):
        self.child_pane.dispatch_event('on_mouse_motion', *args)

    def on_mouse_press(self, *args):
        self.child_pane.dispatch_event('on_mouse_press', *args)

    def on_mouse_release(self, *args):
        self.child_pane.dispatch_event('on_mouse_release', *args)

    def on_mouse_scroll(self, *args):
        self.child_pane.dispatch_event('on_mouse_scroll', *args)

    def on_resize(self, width, height):
        self.child_pane.change_dims(0, 0, width, height)


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
            pane = Pane(x0, y0, x1, y1)
            child.attach(pane)
            pane.push_handlers(self.on_content_resize)

    def detach(self):
        super().deattach()
        for child in self.children:
            child.pane.remove_handlers(self)
            child.detach()

    def add_child(self, child: View):
        self._add_child_noresize(child)
        self._resize()

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
        self._resize()

    def _resize(self):
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
            pane = Pane(x0, y0, x1, y1)
            child.attach(pane)
            pane.push_handlers(self.on_content_resize)

    def detach(self):
        super().deattach()
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


class TextInput(View):
    def __init__(self, focus_manager, text_color=(192, 192, 192, 255),
                 **kwargs):
        super().__init__(**kwargs)
        self.document = pyglet.text.document.UnformattedDocument('')
        self.document.set_style(0, 0, {'color': text_color})
        self.layout = None
        self.caret = None
        self.focus_manager = focus_manager
        self.text_color = text_color

    def attach(self, pane):
        # TODO: Override detach.
        super().attach(pane)
        self.layout = pyglet.text.layout.IncrementalTextLayout(
            self.document, pane.width - 10, pane.height - 10, multiline=True,
            wrap_lines=True)
        self.layout.x = pane.x0 + 5
        self.layout.y = pane.y0 + 5
        self.caret = pyglet.text.caret.Caret(self.layout,
                                             color=self.text_color[:3])
        self.caret.visible = False
        self.focus_manager.add_input(self)

    def on_resize(self, width, height, offset_x, offset_y):
        if width <= 0 or height <= 0:
            self.caret.visible = False
            return
        self.layout.width = width - 10
        self.layout.height = height - 10
        self.layout.x = offset_x + 5
        self.layout.y = offset_y + 5

    def on_draw(self):
        lines = [
            self.pane.x0 + 2.5, self.pane.y0 + 2.5,
            self.pane.x1 - 2.5, self.pane.y0 + 2.5,
            self.pane.x1 - 2.5, self.pane.y1 - 2.5,
            self.pane.x0 + 2.5, self.pane.y1 - 2.5
        ]  # yapf: disable
        if self.pane.mouseover:
            colors = [192, 192, 192] * (len(lines) // 2)
        else:
            colors = [128, 128, 128] * (len(lines) // 2)

        pyglet.gl.glLineWidth(1)
        pyglet.graphics.draw(
            len(lines) // 2, pyglet.gl.GL_LINE_LOOP, ('v2f', lines),
            ('c3B', colors))

        self.layout.draw()

    def on_return(self):
        pass


class Text(View):
    def __init__(self, text='', get_text=None, color=(255, 255, 255, 255),
                 font_size=None, valign='top', kerning=0, align='left',
                 padding=5, multiline=False, **kwargs):
        super().__init__(**kwargs)
        self.document = pyglet.text.document.UnformattedDocument(text)
        self._style = {
            'color': color,
            'font_size': font_size,
            'kerning': kerning,
            'align': align
        }
        self.document.set_style(0, 0, self._style)
        self.layout = None
        self.multiline = multiline
        self.padding = padding
        self.get_text = get_text
        self.document.text = text
        self.valign = valign

    def _create_layout(self, width, height, offset_x, offset_y):
        self.layout = pyglet.text.layout.IncrementalTextLayout(
            self.document, width - 2 * self.padding, height - 2 * self.padding,
            multiline=self.multiline, wrap_lines=True)
        self.layout.content_valign = self.valign
        self.layout.x = offset_x + self.padding
        self.layout.y = offset_y + self.padding

    def attach(self, pane):
        super().attach(pane)
        if pane.width > 0:
            self._create_layout(pane.width, pane.height, pane.x0, pane.y0)

    def on_resize(self, width, height, offset_x, offset_y):
        if width <= 0:
            self.layout = None
            return
        if self.layout is None:
            self._create_layout(width, height, offset_x, offset_y)
            return
        self.layout.width = width - 2 * self.padding
        self.layout.height = height - 2 * self.padding
        self.layout.x = offset_x + self.padding
        self.layout.y = offset_y + self.padding

    def on_draw(self):
        assert self.layout is not None
        if self.get_text is not None:
            self.document.text = self.get_text()
        self.layout.draw()


class Image(View):
    def __init__(self, image=None, get_image=None, **kwargs):
        super().__init__(**kwargs)
        self.image = image
        self.get_image = get_image

    def on_draw(self):
        if self.get_image is not None:
            self.image = self.get_image()
        if self.image is not None:
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            self.image.blit(self.pane.x0, self.pane.y0, width=self.pane.width,
                            height=self.pane.height)


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

    @event.priority(1)
    def on_mouse_press(self, x, y, button, modifiers):
        target = self._find_input(x, y)
        if target is not self._focus and self._focus is not None:
            self._focus.caret.visible = False
        self._focus = target
        if target is not None:
            self._focus.caret.visible = True
            return target.caret.on_mouse_press(x, y, button, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        target = self._find_input(x, y)
        self.window.set_mouse_cursor(
            None if target is None else self._text_cursor)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._focus:
            return self._focus.caret.on_mouse_drag(x, y, dx, dy, buttons,
                                                   modifiers)

    def on_text(self, text):
        if self._focus:
            return self._focus.caret.on_text(text)

    def on_text_motion(self, motion):
        if self._focus:
            return self._focus.caret.on_text_motion(motion)

    def on_text_motion_select(self, motion):
        if self._focus:
            return self._focus.caret.on_text_motion_select(motion)

    @event.priority(1)
    def on_key_press(self, symbol, modifiers):
        if not self._focus:
            return event.EVENT_UNHANDLED
        if symbol == key.ESCAPE:
            self._focus.caret.visible = False
            self._focus = None
            return event.EVENT_HANDLED
        if symbol in (key.ENTER, key.NUM_ENTER):
            return self._focus.on_return()

        if symbol is not None and (key.SPACE <= symbol <= key.ASCIITILDE
                                   or symbol
                                   in (key.UP, key.RIGHT, key.DOWN, key.LEFT,
                                       key.BACKSPACE, key.DELETE)):
            return event.EVENT_HANDLED
        return event.EVENT_UNHANDLED
