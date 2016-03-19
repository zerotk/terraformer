"""
    LRU module. Based around heapq.
"""
from __future__ import unicode_literals

import itertools
from heapq import heapify, heappop, heappush

from zerotk.terraformer.decorators import Override

DEFAULT_LRU_SIZE = 50


class _Node(object):
    """
    Node with key, object and the last access time.

    Identity hashable and comparable.
    """

    __slots__ = 'key obj node_time size'.split()

    def __init__(self, key, obj, node_time, size):
        """
        :param object key:
            The key this node is storing

        :param object obj:
            The object this node is storing

        :param int node_time:
            The last time this node changed

        :param int size:
            The size of this object
        """
        self.key = key
        self.obj = obj
        self.node_time = node_time
        self.size = size

    def __le__(self, other):
        """
        Compares if less than other item (used by heapify).

        :param _Node other:
            The node to compare: It's currently based on the node_time.
        """
        return self.node_time < other.node_time

    def __cmp__(self, other):
        """
        Compares if less than other item (used by sort).

        :param _Node other:
            The node to compare: It's currently based on the node_time.
        """
        if self.node_time < other.node_time:
            return - 1
        if self.node_time > other.node_time:
            return 1
        return 0

    def __repr__(self):
        """
        :rtype: unicode
        :returns:
            The representation of the item
        """
        return '_Node(time=%s)' % self.node_time


#=========================================================================
# LRU
#=========================================================================
class LRU(object):
    """
    Least Recently Used (LRU) cache.

    Based on heapq module (which is used to guarantee that the 1st item in _heap is
    always the item that has the lowest access time).
    """

    def __init__(self, size=DEFAULT_LRU_SIZE, internal_dict=None, get_size=lambda x: 1):
        """
        :param int size:
            The maximum size for this cache.

        :param dict internal_dict:
            If passed, this will be used as the internal dictionary in this LRU.
        """
        if size <= 0:
            raise ValueError('Size must be > 0. Found: %s' % (size,))

        self._heap = []
        if internal_dict is None:
            self._dict = {}
        else:
            self._dict = internal_dict

        self._maxsize = size
        self._currsize = 0
        self._get_size = get_size
        self._next_access = itertools.count(0).next

        # If a sort is requested, we need to check for both: heapify and sort
        # (if either is True, we need to sort: when sorted, the heap invariants are correct)
        # In sum: For few items it's OK just to heapify/heappush/heappop, but if traversing
        # all items, keeping it sorted instead of heapify/heappop is faster)
        self._heapify_needed = False
        self._sort_needed = False

        # For speed
        self._dict_get = self._dict.get

    def clear(self):
        """
        Clears the LRU also reseting internal variables. The final state after a clear is the same
        as if the LRU was recently created.
        """
        del self._heap[:]
        self._dict.clear()
        self._currsize = 0
        self._heapify_needed = False
        self._sort_needed = False

    def __len__(self):
        """
        :rtype: int
        :returns:
            The current size of the cache
        """
        return len(self._dict)

    def __contains__(self, key):
        """
        :rtype: bool
        :returns:
            True if the key is in the cache and False otherwise.
        """
        return key in self._dict

    has_key = __contains__

    def __setitem__(self, key, obj):
        """
        Sets an item in the cache (with the proper access time)

        :param object key:
            The key to be gotten

        :rtype: object
        :returns:
            The value that was stored for the given item

        :raises KeyError:
            If the key is not available
        """
        node = self._dict_get(key, None)
        add_size = self._get_size(obj)
        if add_size <= 0:
            raise ValueError('Size for object may not be 0. Key: %s' % (key,))

        maxsize = self._maxsize
        currsize = self._currsize

        if node is not None:
            currsize -= node.size

            need_remove = add_size > node.size and currsize + add_size > maxsize

            node.obj = obj
            node.size = add_size
            currsize += add_size
            node.node_time = self._next_access()

            if need_remove:
                # Note, if this becomes slow, we could code around other mechanisms (and
                # not heapq)
                heapify(self._heap)
                self._heapify_needed = False

                # Make it smaller before putting the new item.
                while currsize > maxsize:
                    lru = heappop(self._heap)
                    node = self._dict.pop(lru.key)
                    currsize -= node.size
            else:
                # Changed time: heap invariant may be broken.
                self._heapify_needed = True

        else:
            # Handle special case where we're inserting a value which can not
            # fit in the LRU.
            if add_size > maxsize:
                self.clear()
                return

            if currsize + add_size > maxsize:
                # Before any other heap* operation, we need to heapify for it to stay
                # ok if it lost the invariant for some reason.
                # (if we only did heappop, heappush and related heap operations, we
                # don't need to heapify, but if we did a direct remove without heappop,
                # the invariant would be lost)
                if self._heapify_needed:

                    # Note, if this becomes slow, we could code around other mechanisms (and
                    # not heapq)
                    heapify(self._heap)
                    self._heapify_needed = False

                # Make it smaller before putting the new item.
                while currsize + add_size > maxsize:
                    lru = heappop(self._heap)
                    node = self._dict.pop(lru.key)
                    currsize -= node.size

            node = _Node(key, obj, self._next_access(), add_size)
            currsize += add_size
            self._dict[key] = node
            if self._heapify_needed:
                # No need to heappush, because we'll need to heapify later
                # anyways (so, use faster op)
                self._heap.append(node)
            else:
                heappush(self._heap, node)

        self._currsize = currsize
        # After a setitem, we always need to resort if needed
        self._sort_needed = True

    def __getitem__(self, key):
        """
        Gets an item from the cache (and updates the access time)

        :param object key:
            The key to be gotten

        :rtype: object
        :returns:
            The value that was stored for the given item

        :raises KeyError:
            If the key is not available
        """
        node = self._dict[key]  # Can throw error here
        node.node_time = self._next_access()
        # Changed time: heap invariant may be broken.
        self._heapify_needed = True

        return node.obj

    def get(self, key, default=None):
        """
        Gets an item from the cache (and updates the access time if it exists)

        :param object key:
            The key to be gotten

        :param object default:
            This is the value to be returned if the key doesn't exist.

        :rtype: object
        :returns:
            The value that was stored for the given item or the default value passed.
        """
        if key in self._dict:
            return self[key]

        return default

    def __delitem__(self, key):
        """
        Deletes an item from the cache

        :param object key:
            The key to be removed

        :rtype: object
        :returns:
            The value that was stored for the given item

        :raises KeyError:
            If the key is not available
        """
        node = self._dict.pop(key)  # can throw KeyError here
        self._currsize -= node.size

        # Remove without the heap invariant (heapify when needed).
        self._heap.remove(node)
        self._heapify_needed = True

        return node.obj

    _SENTINEL = []

    def pop(self, key, default=_SENTINEL):
        try:
            return self.__delitem__(key)
        except KeyError:
            if default is not self._SENTINEL:
                return default
            raise

    #--- Iterating
    def iternodes(self):
        """
        :rtype: iterator(_Node)
        :returns:
            Iterator that traverses nodes according to LRU
            (the ones with lowest access time come before)
        """
        # Sorts if either the heapify or sort in needed
        if self._heapify_needed or self._sort_needed:
            self._heap.sort()

            self._sort_needed = False
            # Sorting means that the heapify requirements are also OK.
            self._heapify_needed = False

        for node in self._heap:
            yield node

    def __iter__(self):
        """
        :rtype: iterator(key)
        :returns:
            Iterator that traverses keys according to LRU
            (the ones with lowest access time come before)
        """
        for node in self.iternodes():
            yield node.key

    iterkeys = __iter__

    def iteritems(self):
        """
        :rtype: iterator(key, value)
        :returns:
            Iterator that traverses (key, value) according to LRU
            (the ones with lowest access time come before)
        """
        for node in self.iternodes():
            yield node.key, node.obj

    def itervalues(self):
        """
        :rtype: iterator(value)
        :returns:
            Iterator that passes values according to LRU
            (the ones with lowest access time come before)
        """
        for node in self.iternodes():
            yield node.obj

    #--- Getting keys or values
    def keys(self):
        """
        :rtype: list
        :returns:
            List of keys according to LRU
            (the ones with lowest access time come before)
        """
        return list(self.iterkeys())

    def values(self):
        """
        :rtype: list
        :returns:
            List of values according to LRU
            (the ones with lowest access time come before)
        """
        return list(self.itervalues())


#=========================================================================
# _DictWithRemovalMemo
#=========================================================================
class _DictWithRemovalMemo(dict):
    """
    Helper to store the removed items on __delitem__.
    """

    def __init__(self):
        dict.__init__(self)
        self.removed_items = []

    def pop(self, key):
        item = dict.pop(self, key)
        self.removed_items.append(item.obj)
        return item

    def __delitem__(self, key):
        item = dict.pop(self, key)
        self.removed_items.append(item.obj)


#=========================================================================
# LRUWithRemovalMemo
#=========================================================================
class LRUWithRemovalMemo(LRU):
    """
    This is an LRU that is able to provide which items were removed from it when another item was
    added and its size would exceed the maximum size.

    Note that as it will keep references alive it must be used with care (so, ideally, any time an
    item is added a call to GetAndClearRemovedItems is done, otherwise the references may stay alive
    much more than they should).

    This is used to handle a maximum number of display lists in the
    RenderWindowWithSharedDisplayLists, so that display lists that are not used anymore are properly
    deleted in the opengl context.

    Note that it will only store the references gotten when the size of the lru would become too big
    or when __delitem__ is called explicitly (not on clear()).
    """

    @Override(LRU.__init__)
    def __init__(self, size=DEFAULT_LRU_SIZE):
        self._internal_dict = _DictWithRemovalMemo()
        LRU.__init__(self, size, self._internal_dict)

    def GetAndClearRemovedItems(self):
        """
        :rtype: list(object)
        :returns:
            Returns a list with the removed objects (and clears them so that a new call to this
            method will not get the same entries again).
        """
        items = self._internal_dict.removed_items
        self._internal_dict.removed_items = []
        return items
