from __future__ import unicode_literals

import warnings

import pytest

from zerotk.decorators import Abstract, Comparable, Deprecated, Implements, Override
from zerotk.terraformer import is_frozen


def testImplements():
    with pytest.raises(AssertionError):
        class IFoo(object):

            def DoIt(self):
                ''

        class Implementation(object):

            @Implements(IFoo.DoIt)
            def DoNotDoIt(self):
                ''

    class IFoo(object):
        def Foo(self):
            '''
            docstring
            '''

    class Impl(object):

        @Implements(IFoo.Foo)
        def Foo(self):
            return self.__class__.__name__

    assert IFoo.Foo.__doc__ == Impl.Foo.__doc__

    # Just for 100% coverage.
    assert Impl().Foo() == 'Impl'


def testOverride():

    def TestOK():

        class A(object):

            def Method(self):
                '''
                docstring
                '''


        class B(A):

            @Override(A.Method)
            def Method(self):
                return 2

        b = B()
        assert b.Method() == 2
        assert A.Method.__doc__ == B.Method.__doc__


    def TestERROR():

        class A(object):

            def MyMethod(self):
                ''


        class B(A):

            @Override(A.Method)  # it will raise an error at this point
            def Method(self):
                ''

    def TestNoMatch():

        class A(object):

            def Method(self):
                ''


        class B(A):

            @Override(A.Method)
            def MethodNoMatch(self):
                ''


    TestOK()
    with pytest.raises(AttributeError):
        TestERROR()

    with pytest.raises(AssertionError):
        TestNoMatch()



def testDeprecated(monkeypatch):

    def MyWarn(*args, **kwargs):
        warn_params.append((args, kwargs))

    monkeypatch.setattr(warnings, 'warn', MyWarn)

    was_development = is_frozen.SetIsDevelopment(True)
    try:
        # Emit messages when in development
        warn_params = []

        # ... deprecation with alternative
        @Deprecated('OtherMethod')
        def Method1():
            pass

        # ... deprecation without alternative
        @Deprecated()
        def Method2():
            pass

        Method1()
        Method2()
        assert warn_params == [
            (("DEPRECATED: 'Method1' is deprecated, use 'OtherMethod' instead",), {'stacklevel': 2}),
            (("DEPRECATED: 'Method2' is deprecated",), {'stacklevel': 2})
        ]

        # No messages on release code
        is_frozen.SetIsDevelopment(False)

        warn_params = []

        @Deprecated()
        def FrozenMethod():
            pass

        FrozenMethod()
        assert warn_params == []
    finally:
        is_frozen.SetIsDevelopment(was_development)


def testAbstract():

    class Alpha(object):

        @Abstract
        def Method(self):
            ''

    alpha = Alpha()
    with pytest.raises(NotImplementedError):
        alpha.Method()


def testComparable():

    @Comparable
    class Alpha(object):

        def __init__(self, v):
            self.v = v

        def _cmpkey(self):
            return self.v

    a = Alpha(1)
    b = Alpha(2)
    c = Alpha(2)

    assert a < b
    assert a <= b
    assert b > a
    assert b >= a

    assert b == c
    assert b >= c
    assert b <= c

    s = set()
    s.add(a)
    assert len(s) == 1

    a1 = Alpha(1)
    s.add(a1)
    assert len(s) == 1
