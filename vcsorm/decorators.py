class IterStreamer(object):
    """
    File-like streaming iterator.
    """
    def __init__(self, func):
        self.func = func

    def __len__(self):
        return self.generator.__len__()

    def __iter__(self):
        return self.iterator

    def __call__(self, *args, **kwargs):
        self.leftover = ''
        self.generator = self.func.__call__(self.obj, *args, **kwargs)
        self.iterator = iter(self.generator)
        return self

    def __get__(self, instance, owner):
        self.cls = owner
        self.obj = instance

        return self.__call__

    def next(self):
        return self.iterator.next()

    def read(self, size):
        data = self.leftover
        count = len(self.leftover)
        try:
            while count < size:
                chunk = self.next()
                data += chunk
                count += len(chunk)
        except StopIteration, e:
            self.leftover = ''
            return data

        if count > size:
            self.leftover = data[size:]

        return data[:size]

