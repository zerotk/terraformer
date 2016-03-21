from __future__ import unicode_literals

from collections import OrderedDict

import pytest
from zerotk.memoize import Memoize


class Test:

    def testMemoizeDefaults(self):
        calls = [0]

        @Memoize
        def Foo(param_1, param_2=None, param_3='default'):
            calls[0] += 1

        Foo('param_1')
        assert calls[0] == 1

        Foo('param_1', None)
        assert calls[0] == 1


    def testMemoizeKwargs(self):
        calls = [0]

        @Memoize
        def Foo(param_1, param_2=None, param_3='default'):
            calls[0] += 1

        Foo('param_1')
        assert calls[0] == 1

        Foo('param_1', param_2=None)
        assert calls[0] == 1

        # Test different call
        Foo('param_1', 'param_2')
        assert calls[0] == 2

        Foo('param_1', param_2='param_2')
        assert calls[0] == 2


    def testMemoizeAndClassmethod(self):
        self._calls = 0
        class F(object):
            NAME = 'F'

            @classmethod
            @Memoize(3)  # Note: cls will be part of the cache-key in the Memoize.
            def GetName(cls, param):
                self._calls += 1
                return cls.NAME + param

        class G(F):
            NAME = 'G'

        assert 'F1' == F.GetName('1')
        assert 'F2' == F.GetName('2')
        assert 'G2' == G.GetName('2')
        assert 3 == self._calls

        assert 'F1' == F.GetName('1')
        assert 3 == self._calls

        assert 'G3' == G.GetName('3')
        assert 4 == self._calls
        assert 'F1' == F.GetName('1')
        assert 5 == self._calls


    def testMemoizeAndMethod(self):
        _calls = []

        class F(object):

            def __init__(self, name):
                self.name = name

            @Memoize(2)
            def GetName(self, param):
                result = self.name + param
                _calls.append(result)
                return result

        f = F('F')
        g = F('G')

        f.GetName('1')
        assert _calls == ['F1']
        f.GetName('2')
        assert _calls == ['F1', 'F2']
        f.GetName('1')
        assert _calls == ['F1', 'F2']  # Cache HIT

        f.GetName('3')
        assert _calls == ['F1', 'F2', 'F3']

        f.GetName('1')
        assert _calls == ['F1', 'F2', 'F3', 'F1']  # Cache miss because F1 was removed

        g.GetName('1')
        g.GetName('2')
        assert _calls == ['F1', 'F2', 'F3', 'F1', 'G1', 'G2']

        g.GetName('2')
        assert _calls == ['F1', 'F2', 'F3', 'F1', 'G1', 'G2']  # Cache HIT because F and G have a separated cache.


    def testMemoizeErrors(self):
        with pytest.raises(TypeError):
            class MyClass(object):

                @Memoize(2)
                @classmethod
                def MyMethod(self):
                    'Not called'

        with pytest.raises(TypeError) as exception:
            number = 999
            Memoize(2)(number)

        assert unicode(exception.value) == 'Expecting a function/method/classmethod for Memoize.'

        with pytest.raises(AssertionError) as exception:
            @Memoize(2, 'INVALID')
            def MyFunction():
                'Not called!'

        assert unicode(exception.value) == 'Memoize prune method not supported: INVALID'


    def testMemoizeLRU(self):
        counts = {
            'Double' : 0,
        }

        @Memoize(2, Memoize.LRU)  # Just 2 values kept
        def Double(x):
            counts['Double'] += 1
            return x * 2
        assert Double.func_name == 'Double'

        assert counts == dict(Double=0)

        # Only the first call with a given argument bumps the call count:
        #
        assert Double(2) == 4
        assert counts['Double'] == 1
        assert Double(2) == 4
        assert counts['Double'] == 1
        assert Double(3) == 6
        assert counts['Double'] == 2

        # Unhashable keys: an error is raised!
        with pytest.raises(TypeError):
            Double([10])

        # Now, let's see if values are discarded when more than 2 are used...
        assert Double(2) == 4
        assert counts['Double'] == 2
        Double(4)  # Now, we have 2 and 4 in the cache
        assert counts['Double'] == 3
        Double(3)  # It has discarded this one, so, it has to be added again!
        assert counts['Double'] == 4

    def testMemoize(self):
        counts = {
            'Double' : 0,
        }

        @Memoize(2, Memoize.FIFO)  # Just 2 values kept
        def Double(x):
            counts['Double'] += 1
            return x * 2
        assert Double.func_name == 'Double'

        assert counts == dict(Double=0)

        # Only the first call with a given argument bumps the call count:
        assert Double(2) == 4
        assert counts['Double'] == 1
        assert Double(2) == 4
        assert counts['Double'] == 1
        assert Double(3) == 6
        assert counts['Double'] == 2

        counts['NoArgs'] = 0

        # Unhashable keys: an error is raised!
        with pytest.raises(TypeError):
            Double([10])

        # Now, let's see if values are discarded when more than 2 are used...
        assert Double(2) == 4
        assert counts['Double'] == 2
        Double(4)
        assert counts['Double'] == 3
        Double(2)  # It has discarded this one, so, it has to be added again!
        assert counts['Double'] == 4

        # Check if it works without any arguments.
        @Memoize
        def NoArgs():
            counts['NoArgs'] += 1
            return 1
        NoArgs()
        NoArgs()
        NoArgs()
        assert counts['NoArgs'] == 1


        #--- Check if the cache is cleared when the instance is removed.
        class Stub(object):
            pass

        self._stub = Stub()
        def _GetRet():
            return self._stub

        class Foo(object):

            def __init__(self):
                self.called = False

            @Memoize(2)
            def m1(self):
                assert not self.called
                self.called = True
                return _GetRet()

        f = Foo()
        assert f.m1() is self._stub

        from zerotk.weak_ref import GetWeakRef
        self._stub = GetWeakRef(self._stub)
        assert f.m1() is self._stub()
        assert f.called

        f2 = Foo()
        assert not f2.called
        f2.m1()
        assert f2.called

        del f
        del f2
        assert self._stub() is None  # Should be garbage-collected at this point!


    def testClearMemo(self):
        self._called = 0
        @Memoize
        def Method(p):
            self._called += 1
            return p

        Method(1)
        Method(1)

        assert self._called == 1
        Method.ClearCache()

        Method(1)
        Method(1)
        assert self._called == 2


    def testClearMemoOnInstance(self):
        self._called = 0
        outer_self = self
        class Bar(object):
            @Memoize
            def m1(self, p):
                outer_self._called += 1
                return p

        b = Bar()
        b.m1(1)
        b.m1(1)
        assert self._called == 1

        b.m1.ClearCache(b)
        b.m1(1)
        assert self._called == 2
        b.m1(1)
        assert self._called == 2


    def testNonDeclaredKeywordArguments(self):
        # Can't declare non-declared keyword arguments.
        def Foo(**args):
            return object()

        with pytest.raises(Exception) as exception_info:
            Memoize(Foo)
        message = 'Non-declared keyword arguments (`**kwargs`) not supported. Note that Memoize must be the first decorator (nearest to the function) used.'
        assert message in unicode(exception_info.value)

        # Can't try to call with non-declared keyword arguments.
        @Memoize
        def Bar(a=0):
            return object()
        Bar(1)
        Bar(a=1)
        with pytest.raises(Exception) as exception_info:
            Bar(s=2)
        message = 'Can\'t use non-declared keyword arguments.'
        assert message in unicode(exception_info.value)

    def testPerformance__flaky(self):
        '''
        Results 2014-07-02 (support for defaults and passing kwargs)
        ---------------------------------------------------------
        call_no_positional is 6.1 times slower than baseline.
        call_with_defaults is 11.2 times slower than baseline.
        call_passing_kwargs is 13.4 times slower than baseline.
        ---------------------------------------------------------


        Results < 2014-07-02
        ---------------------------------------------------------
        call_no_positional is 5.3 times slower than baseline.
        call_with_defaults (no support)
        call_passing_kwargs (no support)
        ---------------------------------------------------------
        '''
        from textwrap import dedent
        import timeit

        for_size = 1000
        repeat = 7
        number = 10
        timing = OrderedDict()

        def Check(name, setup, stmt):
            timer = timeit.Timer(
                setup=(dedent(setup)),
                stmt=(dedent(stmt)),
            )
            timing[name] = min(timer.repeat(repeat=repeat, number=number))


        PRINT_PERFORMANCE = False
        def PrintPerformance(timing, name):
            if PRINT_PERFORMANCE:
                print '%s is %.1f times slower than baseline.' % (name, timing[name] / timing['baseline'])

        # Baseline
        Check(
            'baseline',
            'from random import Random;r = Random(1)',
            "for _i in xrange(%d): tuple((r.random(), 'g/cm3', 'density'))" % (for_size,)
            )


        Check(
            'call_no_positional',
            '''
            from zerotk.memoize import Memoize

            @Memoize
            def Foo(arg1, arg2):
                pass
            ''',
            "for _i in xrange(%d): Foo('arg1', 'arg2'); Foo('arg1', 'arg2')" % (for_size,)
            )
        PrintPerformance(timing, 'call_no_positional')

        Check(
            'call_with_defaults',
            '''
            from zerotk.memoize import Memoize

            @Memoize
            def Foo(arg1, arg2=None):
                pass
            ''',
            "for _i in xrange(%d): Foo('arg1'); Foo('arg1', 'arg2')" % (for_size,)
            )
        PrintPerformance(timing, 'call_with_defaults')

        Check(
            'call_passing_kwargs',
            '''
            from zerotk.memoize import Memoize

            @Memoize
            def Foo(arg1, arg2=None):
                pass
            ''',
            "for _i in xrange(%d): Foo('arg1'); Foo('arg1', arg2='arg2')" % (for_size,)
            )
        PrintPerformance(timing, 'call_passing_kwargs')

    def profileMemoize(self):
        from ben10.debug.profiling import PrintProfileMultiple, ProfileMethod

        @Memoize(maxsize=1, prune_method=Memoize.LRU)
        def Call():
            return 1

        @ProfileMethod('test.prof')
        def Check():

            for _i in xrange(100000):
                Call()

        Check()
        PrintProfileMultiple('test.prof')
