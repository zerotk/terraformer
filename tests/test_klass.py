from __future__ import unicode_literals
from zerotk.terraformer.klass import (AllBasesNames, CheckOverridden,
                                      GetClassHierarchy, IsInstance, IsSubclass)
import pytest


class _A(object):
    pass


class _B(object):
    pass


class _C(_B):
    pass


class _D(_C, _A):
    pass


class _E(_D, _C, _A):
    pass


class Test:

    def testClassHierarchy(self):

        # check when cache is active
        assert set([_E, _D, _C, _B, _A, object]) == GetClassHierarchy(_E)
        assert set([_E, _D, _C, _B, _A, object]) == GetClassHierarchy(_E)

        assert set([_D, _C, _B, _A, object]) == GetClassHierarchy(_D)
        assert set([_C, _B, object]) == GetClassHierarchy(_C)

        # check when cache is active
        assert set([_A, object]) == GetClassHierarchy(_A)
        assert set([_A, object]) == GetClassHierarchy(_A)

    def testIsInstance(self):
        assert IsInstance(_C(), '_B')
        assert IsInstance(_C(), ('_B',))
        assert not IsInstance(_C(), ('_A',))
        assert IsInstance(_C(), ('_A', '_B'))
        assert not IsInstance(_C(), ('_A', '_D'))

    def testIsSubclass(self):
        assert IsSubclass(_C, ('_C',))
        assert IsSubclass(_C, '_B')
        assert IsSubclass(_C, ('_B',))
        assert not IsSubclass(_C, ('_A',))
        assert IsSubclass(_C, ('_A', '_B'))
        assert not IsSubclass(_C, ('_A', '_D'))
        assert not IsSubclass(_A, ('_C',))

    def test_klass__serial(self):

        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        class D(C):
            pass

        class Alpha(object):
            pass

        class AlphaC(Alpha, C):
            pass

        assert set(AllBasesNames(A)) == set(['object'])
        assert set(AllBasesNames(B)) == set(['A', 'object'])
        assert set(AllBasesNames(C)) == set(['B', 'A', 'object'])
        assert set(AllBasesNames(D)) == set(['C', 'B', 'A', 'object'])
        assert set(AllBasesNames(AlphaC)) == set(
            ['Alpha', 'object', 'C', 'B', 'A'])

        assert IsInstance(A(), 'object')
        assert IsInstance(A(), 'A')
        assert IsInstance(B(), 'object')
        assert IsInstance(B(), 'A')
        assert IsInstance(B(), 'B')
        assert IsInstance(C(), 'object')
        assert IsInstance(C(), 'A')
        assert IsInstance(C(), 'B')
        assert IsInstance(C(), 'C')
        assert IsInstance(AlphaC(), 'object')
        assert IsInstance(AlphaC(), 'A')
        assert IsInstance(AlphaC(), A)
        assert IsInstance(AlphaC(), 'B')
        assert IsInstance(AlphaC(), 'C')
        assert IsInstance(AlphaC(), 'Alpha')
        assert IsInstance(AlphaC(), 'AlphaC')
        assert IsInstance(AlphaC(), AlphaC)

        assert not IsInstance(AlphaC(), 'Rubles')
        assert not IsInstance(A(), 'B')
        assert not IsInstance(B(), 'C')

# TODO: BEN-18: Improve coverage.
#       Not executed on tests... might as well be commented. Create a test for it.
#     def profileIsInstance(self):
#         '''
#             Results obtained (after optimizing):
#                 Unnamed Timer: IsInstance unicode 0.131 secs
#                 Unnamed Timer: IsInstance tuple 0.244 secs
#                 Unnamed Timer: isinstance 0.041 secs
#
#                 With timeit implementation
#                 IsInstance unicode 1.28110317487
#                 IsInstance tuple 2.4118422541
#                 isinstance 0.376544210033
#
#                 Changes: using IsSubclass
#                 IsInstance unicode 1.52469482232
#                 IsInstance tuple 2.62789000656
#                 IsInstance classs 2.18690264229
#                 isinstance 0.402243563057
#         '''
#         import timeit
#
#         setup = 'from __main__ import A, B, C, D, E;from coilib50.basic.klass import IsInstance'
#
#         timer = timeit.Timer(stmt='IsInstance(C(), "B")', setup=setup)
#         print 'IsInstance unicode', timer.timeit()
#
#         timer = timeit.Timer(stmt='IsInstance(C(), ("B", ))', setup=setup)
#         print 'IsInstance tuple', timer.timeit()
#
#         timer = timeit.Timer(stmt='IsInstance(C(), B)', setup=setup)
#         print 'IsInstance class', timer.timeit()
#
#         timer = timeit.Timer(stmt='isinstance(C(), B)', setup=setup)
#         print 'isinstance', timer.timeit()

    def testIsInstanceWithDateTime(self):
        '''
        Make sure IsInstance works with DateTime objects.

        Previously passing a DateTime to IsInstance would yield an
        AttributeError for __class__. Changed IsInstance to use type() instead.
        '''
        mx_dt = pytest.importorskip('mx.DateTime')
        assert IsInstance(mx_dt.DateTime(2012), 'DateTime')
        assert not IsInstance(mx_dt.DateTime(2012), 'Scalar')

    def testCheckOverridden(self):
        class A(object):

            def m1(self):
                pass

            def m2(self):
                pass

        class B(A):

            def m1(self):
                pass

        class C(A):

            def m2(self):
                pass

        CheckOverridden(B(), A, 'm1')
        CheckOverridden(C(), A, 'm2')
        with pytest.raises(AssertionError):
            CheckOverridden(B(), A, 'm2')

        # Wrong hierarchy:
        with pytest.raises(AssertionError):
            CheckOverridden(C(), B, 'm1')

        with pytest.raises(AssertionError):
            CheckOverridden(A(), B, 'm1')
