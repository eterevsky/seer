import pyglet.graphics
import unittest
from unittest.mock import Mock, patch

from .observable import Attribute, Observable, make_observable
from .pane import Pane


class PaneTest(unittest.TestCase):
    @patch('pyglet.graphics.draw')
    def test_with_background(self, mock_draw):
        pane = Pane(0, 0, 100, 100, background=(127, 127, 127))
        pane.dispatch_event('on_draw')
        mock_draw.assert_called_once_with(6, pyglet.gl.GL_TRIANGLES, ('v2f', [
            0, 0, 100, 0, 100, 100, 0, 0, 100, 100, 0, 100
        ]), ('c3B', (127, ) * 18))

    @patch('pyglet.graphics.draw')
    def test_no_background(self, mock_draw):
        pane = Pane(0, 0, 100, 100)
        pane.dispatch_event('on_draw')
        mock_draw.assert_not_called()

    @patch('pyglet.graphics.draw')
    def test_update_background(self, mock_draw):
        pane = Pane(0, 0, 100, 100, background=(127, 127, 127))
        pane.coords = (100, 100, 200, 200)
        pane.background_color = (255, 255, 255)
        pane.dispatch_event('on_draw')
        mock_draw.assert_called_once_with(6, pyglet.gl.GL_TRIANGLES, ('v2f', [
            100, 100, 200, 100, 200, 200, 100, 100, 200, 200, 100, 200
        ]), ('c3B', (255, ) * 18))


if __name__ == '__main__':
    unittest.main()