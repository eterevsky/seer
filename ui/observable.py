from typing import Any, Callable, List, Union


class Observable(object):
    """An observable value.

    A object of this class holds a single value. Any number of listeners can be
    registered, that will be called when the value is modified. If `o` is
    an observable value:

    `o.value` is the current value.

    `o.set(val)` will update the value and possibly call the observers.
    The observers *will not be called* if the new value is equal to the old one.

    `o.observe(callback)` registers a callback that will be called every time
    the value is modified. The callbacks are called in the order of
    registration.

    `o.remove_observer(callback_or_object)` unregisters observer(s)
    """
    def __init__(self, value: Any = None):
        """Initializes the observable value.

        Args:
            value: initial value or None by default.
        """
        self.value: Any = value
        self._observers: List[Callable] = []

    def set(self, value: Any):
        """Updates the value and calls the observers.

        The observers *will not be called* if the new value is equal to
        the old one.
        """
        if self.value != value:
            self.value = value
            for observer in self._observers:
                observer(self.value)

    def observe(self, observer: Callable):
        """Registers an observer callback.

        The callback is added to the end of the queue of observers. When the
        value changes it will be called with its new value as a single argument.
        """
        self._observers.append(observer)

    def remove_observer(self, observer: Any):
        """Unregisers observer callbacks(s).

        Args:
            `observer`: If it is a function, it will be removed from the list of
              observers directly. If it's an object, any observers that are
              methods of this class will be removed.
        """
        i = 0
        while i < len(self._observers):
            if (self._observers[i] is observer or
                    getattr(self._observers[i], '__self__', None) is observer):
                del self._observers[i]
            else:
                i += 1