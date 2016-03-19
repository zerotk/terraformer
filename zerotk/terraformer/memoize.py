from __future__ import unicode_literals

from collections import OrderedDict


class Memoize(object):
    """
    This class is meant to be used as a decorator.

    It decorates a class so that values can be cached (and later pruned from that cache).

    Usage:
        class Foo(object):

            @Memoize(2, Memoize.FIFO)  #means that max_size == 2 and we want to use a FIFO.
            def double(self, x):
                return x * 2

        or
        @Memoize
        def double(x):
            return x * 2

    This implementation supposes that the arguments are already immutable and won't change.
    If some function needs special behavior, this class should be subclassed and _GetCacheKey
    should be overridden.

    Note that the 1st parameter will determine whether it should be used as an instance method
    or a function (It'll just check if the 1st parameter is 'self', and if it is, an
    instance method is used). If this behavior is not wanted, the memo_target must be forced
    to MEMO_INSTANCE_METHOD or MEMO_FUNCTION.

    Note that non-declared keyword arguments (`**kwargs`) are forbidden. Offer proper support for it may cause a
    prohibitive overhead.
    """

    # This should be the simplest (and fastest) way of caching things: what gets in first
    # is removed first.
    FIFO = 'FIFO'
    LRU = 'LRU'

    MEMO_INSTANCE_METHOD = 'instance_method'
    MEMO_FUNCTION = 'function'
    MEMO_FROM_ARGSPEC = 'from_argspec'


    def __new__(cls, *args, **kwargs):
        """
        We have to override __new__ so that we treat receiving it with and without parameters,
        as the parameters are both optional and we want to support receiving it without parameters.

        E.g.:
        @Memoize
        def double(x):
            return x * 2
        """

        if not kwargs and len(args) == 1 and not isinstance(args[0], int):
            # We received a single argument and it's a function (no parameters received:
            # at this point we have to really instance and already make the __call__)
            ret = object.__new__(cls)
            ret.__class__.__init__(ret)
            ret = ret.__call__(args[0])
            return ret

        ret = object.__new__(cls)
        return ret


    def __init__(self, maxsize=50, prune_method=FIFO, memo_target=MEMO_FROM_ARGSPEC):
        """
        :param int maxsize:
            The maximum size of the internal cache (default is 50).

        :param unicode prune_method:
            This is according to the way used to prune entries. Right now only
            pruning the oldest entry is supported (FIFO), but different ways could be
            available (e.g.: pruning LRU seems a natural addition)

        :param unicode memo_target:
            One of the constants MEMO_INSTANCE_METHOD or MEMO_FUNCTION or MEMO_FROM_ARGSPEC.
            When from argspec it'll try to see if the 1st parameter is 'self' and if it is,
            it'll fall to using the MEMO_INSTANCE_METHOD (otherwise the MEMO_FUNCTION is used)
            If the signature of the function is 'special' and doesn't follow the conventions,
            the memo_target MUST be specified.
        """

        self._prune_method = prune_method
        self._maxsize = maxsize
        self._memo_target = memo_target


    def _GetCacheKey(self, args, kwargs):
        """
        Subclasses may override to provide a different cache key. The default implementation
        just handles the arguments.

        :param list args:
            The arguments received.

        :param dict kwargs:
            The keyword arguments received.

        :return tuple:
            A tuple representing a call to our memoized function.

            This tuple is normalized with values for all arguments that the function receives,
            based on `args` and `kwargs` passed in this call, in addition to any default values.
        """
        # `argspec` list explicitly declared parameters and their default values.
        has_default, argspec = self._argspec

        if kwargs:
            named_arguments_count = len(argspec)
            # If we received kwargs, set them in our argspec, as if that was the default value.
            argspec = argspec.copy()
            for k, v in kwargs.iteritems():
                argspec[k] = v
            # If argspec have been extended we got non-declared keyword arguments. And that is forbidden.
            if named_arguments_count != len(argspec):
                raise ValueError('Can\'t use non-declared keyword arguments.')

        elif not has_default:
            # If we got not kwargs, and there is no default all parameters must be present (and maybe some varargs).
            # The calling arguments alone are a good cache key.
            return args

        # Obtain key from the args we received, plus whatever defaults we have in our argspec.
        return args + tuple(argspec.values()[len(args):])


    def _GetArgspecObject(self, args, trail, kwargs, defaults):
        """
        Create the argspec object that helps when creating the cache key. Subclasses may want to customize the argspec
        object to help offer customized cache key generation algorithm.

        :param list(unicode) args:
            The names of the explicit arguments.
        :param unicode trail:
            The variable name used to store varargs.
            `None` if no varargs are accepted.
        :param unicode kwargs:
            The variable name used to store non-explict keyword arguments.
             `None` if no non-explicit keyword arguments are accepted.
        :param tuple(object) defaults:
            The default values (when existent) for the variable listed in the `args` parameter.
            When not all parameter have default values this tuple will have less elements than `args`. Given the
            function `def Foo(a, b, c=3, d=4): pass` than `args == ['a', 'b', 'c', 'd']` and `defaults == (3, 4)`.
            `None` if there are no defaults.
        :rtype: object
        :return:
            This object will be set as `self._argspec`, this object can be used by `self._GetCacheKey`.
            The base class uses a tuple with a bool indication if default are present and a `coilib50.basic.odict.odict`
            that is a mapping of "parameter name" -> "default value" (a string is used when the is no default).
        """
        named_arguments = OrderedDict()
        if kwargs is not None:
            raise TypeError(
                'Non-declared keyword arguments (`**kwargs`) not supported.'
                ' Note that Memoize must be the first decorator (nearest to the function) used.'
            )
        if defaults is None:
            has_defaults = False
            defaults = ()
        else:
            has_defaults = True
        if self._memo_target == self.MEMO_INSTANCE_METHOD:
            args = args[1:]  # Ignore self when dealing with instance method
        first_default = len(args) - len(defaults)
        for i, arg in enumerate(args):
            if i < first_default:
                named_arguments[arg] = '@Memoize: no_default'
            else:
                named_arguments[arg] = defaults[i - first_default]
        return has_defaults, named_arguments


    def __call__(self, func):
        """
        :param function func:
            This is the function which should be decorated.

        :return function:
            The function decorated to cache the values based on the arguments.
        """
        import inspect

        if self._memo_target == self.MEMO_FROM_ARGSPEC:
            check_func = func
            if inspect.ismethod(check_func):
                check_func = check_func.im_func

            if not inspect.isfunction(check_func):
                if type(check_func) == classmethod:
                    raise TypeError(
                        'To declare a classmethod with Memoize, the Memoize must be called before '
                        'the classmethod\n(will work as a global cache where cls will be part of the '
                        'cache-key).')
                else:
                    raise TypeError('Expecting a function/method/classmethod for Memoize.')
            else:
                if 'self' in check_func.func_code.co_varnames:
                    self._memo_target = self.MEMO_INSTANCE_METHOD
                else:
                    # If it's a classmethod, it should enter here (and the cls will
                    # be used as a part of the cache key, so, all should work properly).
                    self._memo_target = self.MEMO_FUNCTION

        # Register argspec details, these are used to normalize cache keys
        self._argspec = self._GetArgspecObject(*inspect.getargspec(func))

        # Create call wrapper, and make it look like the real function
        call = self._CreateCallWrapper(func)
        call.func_name = func.func_name
        call.__name__ = func.__name__
        call.__doc__ = func.__doc__
        return call


    def _CreateCacheObject(self):
        """
        Creates the cache object we want.

        :returns object:
            The object to be used as the cache (will prune items after the maximum size
            is reached).

            This object has a dict interface.
        """
        if self._prune_method == self.FIFO:
            from .fifo import FIFO
            return FIFO(self._maxsize)

        elif self._prune_method == self.LRU:
            from .lru import LRU
            return LRU(self._maxsize)

        else:
            raise AssertionError('Memoize prune method not supported: %s' % self._prune_method)


    def _CreateCallWrapper(self, func):
        """
        This function creates a FIFO cache

        :param object func:
            This is the function that is being cached.
        """
        SENTINEL = []
        if self._memo_target == self.MEMO_INSTANCE_METHOD:

            outer_self = self
            cache_name = '__%s_cache__' % func.__name__

            def Call(self, *args, **kwargs):
                cache = getattr(self, cache_name, None)
                if cache is None:
                    cache = outer_self._CreateCacheObject()
                    setattr(self, cache_name, cache)

                #--- GetFromCacheOrCreate: inlined for speed
                key = outer_self._GetCacheKey(args, kwargs)
                res = cache.get(key, SENTINEL)
                if res is SENTINEL:
                    res = func(self, *args, **kwargs)
                    cache[key] = res
                return res

            def ClearCache(self):
                """
                Clears the cache for a given instance (note that self must be passed as a parameter).
                """
                cache = getattr(self, cache_name, None)
                if cache is not None:
                    cache.clear()

            Call.ClearCache = ClearCache
            return Call

        elif self._memo_target == self.MEMO_FUNCTION:

            # When it's a function, we can use the same cache the whole time (i.e.: it's global)
            cache = self._CreateCacheObject()
            def Call(*args, **kwargs):
                #--- GetFromCacheOrCreate: inlined for speed
                key = self._GetCacheKey(args, kwargs)
                res = cache.get(key, SENTINEL)
                if res is SENTINEL:
                    res = func(*args, **kwargs)
                    cache[key] = res
                return res

            Call.ClearCache = cache.clear
            return Call

        else:
            raise AssertionError("Don't know how to deal with memo target: %s" % self._memo_target)
