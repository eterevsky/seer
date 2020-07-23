import unittest
from unittest.mock import Mock, patch

from .layout import RootLayout
from .observable import Attribute, Observable, make_observable
from .pane import Pane
from .view import View


class MyView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_draw_calls = 0

    def on_draw(self):
        self.on_draw_calls += 1


class RootLayoutTest(unittest.TestCase):
    def test_init_root(self):
        window = Mock()
        window.width = 200
        window.height = 100
        view = MyView(background_color=(1, 2, 3))

        layout = RootLayout(window, view)
        self.assertEqual(layout.child_pane.background_color, (1, 2, 3))
        layout.on_draw()

        self.assertEqual(view.on_draw_calls, 1)

        other_view = View()
        layout.child = other_view

        self.assertEqual(layout.child_pane.background_color, None)
        layout.on_draw()
        self.assertEqual(view.on_draw_calls, 1)

    def test_mouseover(self):
        window = Mock()
        window.width = 200
        window.height = 100
        layout = RootLayout(window)

        callback = Mock()
        layout.child_pane.mouse_pos_.observe(callback)
        self.assertEqual(layout.child_pane.mouse_pos, None)

        layout.on_mouse_leave(1, 2)
        callback.assert_not_called()
        self.assertEqual(layout.child_pane.mouse_pos, None)

        layout.on_mouse_enter(50, 50)
        callback.assert_called_once_with((50, 50))
        callback.reset_mock()
        self.assertEqual(layout.child_pane.mouse_pos, (50, 50))

        layout.on_mouse_motion(51, 51, 1, 1)
        callback.assert_called_once_with((51, 51))
        callback.reset_mock()
        self.assertEqual(layout.child_pane.mouse_pos, (51, 51))
