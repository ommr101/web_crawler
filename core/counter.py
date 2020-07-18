import threading


class Counter:
    def __init__(self, initial=0):
        self.value = initial
        self._lock = threading.Lock()

    def __add__(self, other):
        with self._lock:
            self.value = self.value + other

        return self

    def __lt__(self, other):
        return self.value < other

    def __gt__(self, other):
        return self.value > other

    def __str__(self):
        return str(self.value)
