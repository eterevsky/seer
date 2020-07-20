import pyglet.shapes
import unittest
from unittest.mock import Mock, patch

from .observable import Attribute, Observable, make_observable
from .pane import Pane


class PaneTest(unittest.TestCase):
    def test_no_background(self):
        pane = Pane(0, 0, 100, 100, Observable(None))
        self.assertEqual(pane._background_shape, None)

    def test_with_background(self):
        pane = Pane(0, 0, 100, 100, Observable(None),
                    background=(127, 127, 127))
        self.assertTrue(
            isinstance(pane._background_shape, pyglet.shapes.Rectangle))
        self.assertEqual(pane._background_shape.x, 0)
        self.assertEqual(pane._background_shape.y, 0)
        self.assertEqual(pane._background_shape.width, 100)
        self.assertEqual(pane._background_shape.height, 100)
        self.assertEqual(pane._background_shape.color, (127, 127, 127))

    def test_update_background(self):
        pane = Pane(0, 0, 100, 100, Observable(None),
                    background=(127, 127, 127))
        pane.coords = (100, 100, 200, 200)
        pane.background_color = (255, 255, 255)
        self.assertTrue(
            isinstance(pane._background_shape, pyglet.shapes.Rectangle))
        self.assertEqual(pane._background_shape.x, 100)
        self.assertEqual(pane._background_shape.y, 100)
        self.assertEqual(pane._background_shape.width, 100)
        self.assertEqual(pane._background_shape.height, 100)
        self.assertEqual(pane._background_shape.color, (255, 255, 255))

    def test_mouseover(self):
        parent_mouse_pos_ = Observable((200, 200))

        pane = Pane(0, 0, 100, 100, parent_mouse_pos_,
                    background=(127, 127, 127))
        callback = Mock()
        pane.mouse_pos_.observe(callback)
        self.assertEqual(pane.mouse_pos, None)

        parent_mouse_pos_.set(None)
        callback.assert_not_called()
        self.assertEqual(pane.mouse_pos, None)

        parent_mouse_pos_.set((50, 50))
        callback.assert_called_once_with((50, 50))
        callback.reset_mock()
        self.assertEqual(pane.mouse_pos, (50, 50))

        parent_mouse_pos_.set((51, 51))
        callback.assert_called_once_with((51, 51))
        callback.reset_mock()
        self.assertEqual(pane.mouse_pos, (51, 51))

        parent_mouse_pos_.set((200, 200))
        callback.assert_called_once_with(None)
        callback.reset_mock()
        self.assertEqual(pane.mouse_pos, None)


if __name__ == '__main__':
    unittest.main()