from pyglet.window import key

from . import event


class FocusManager(object):
    def __init__(self, window):
        self.window = window
        window.push_handlers(self)
        self._inputs = []
        self._focus = None
        self._text_cursor = window.get_system_mouse_cursor('text')

    def add_input(self, controller):
        self._inputs.append(controller)

    def focus(self, input):
        self._focus = input

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
