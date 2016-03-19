from __future__ import unicode_literals
from collections import OrderedDict


class FIFO(OrderedDict):
    '''
    This is a First in, First out cache, so, when the maximum size is reached, the first item added
    is removed.
    '''

    def __init__(self, maxsize):
        '''
        :param int maxsize:
            The maximum size of this cache.
        '''
        OrderedDict.__init__(self)
        self._maxsize = maxsize


    def __setitem__(self, key, value):
        '''
        Sets an item in the cache. Pops items as needed so that the max size is never passed.

        :param object key:
            Key to be set

        :param object value:
            Corresponding value to be set for the given key
        '''
        l = len(self)

        # Note, we must pop items before adding the new one to the cache so that
        # the size does not exceed the maximum at any time.
        while l >= self._maxsize:
            l -= 1
            # Pop the first item created
            self.popitem(0)

        OrderedDict.__setitem__(self, key, value)
