import unittest
from unittest.mock import Mock

from .observable import Observable


class ObservableTest(unittest.TestCase):
    def test_observe(self):
        v = Observable(1)
        callback1 = Mock()
        callback2 = Mock()
        v.observe(callback1)
        v.observe(callback2)
        v.set(1)
        callback1.assert_not_called()
        callback2.assert_not_called()
        v.set(2)
        callback1.assert_called_once_with(2)
        callback2.assert_called_once_with(2)

    def test_remove(self):
        called = 0
        def observer(v):
            nonlocal called
            called += 1
        v = Observable(1)
        v.observe(observer)
        v.set(2)
        self.assertEqual(called, 1)
        v.remove_observer(observer)
        v.set(3)
        self.assertEqual(called, 1)



if __name__ == '__main__':
    unittest.main()