from __future__ import unicode_literals

import sys
import weakref

import pytest
import six

from zerotk.weak_ref import (
    GetRealObj, GetWeakProxy, GetWeakRef, IsSame, IsWeakProxy, IsWeakRef,
    WeakList, WeakMethodProxy, WeakMethodRef, WeakSet)


class _Stub(object):

    def __hash__(self):
        return 1

    def __eq__(self, o):
        return True  # always equal

    def __ne__(self, o):
        return not self == o

    def Method(self):
        pass


class Test():

    def testStub(self):
        a = _Stub()
        b = _Stub()
        assert not a != a
        assert not a != b
        assert a == a
        assert a == b
        a.Method()

    def testIsSame(self):
        s1 = _Stub()
        s2 = _Stub()

        r1 = weakref.ref(s1)
        r2 = weakref.ref(s2)

        p1 = weakref.proxy(s1)
        p2 = weakref.proxy(s2)

        assert IsSame(s1, s1)
        assert not IsSame(s1, s2)

        assert IsSame(s1, r1)
        assert IsSame(s1, p1)

        assert not IsSame(s1, r2)
        assert not IsSame(s1, p2)

        assert IsSame(p2, r2)
        assert IsSame(r1, p1)
        assert not IsSame(r1, p2)

        with pytest.raises(ReferenceError):
            IsSame(p1, p2)

    def testGetWeakRef(self):
        b = GetWeakRef(None)
        assert b() is None

    def testGeneral(self):
        b = _Stub()
        r = GetWeakRef(b.Method)
        assert r() is not None  # should not be a regular weak ref here (but a weak method ref)

        assert IsWeakRef(r)
        assert not IsWeakProxy(r)

        r = GetWeakProxy(b.Method)
        r()
        assert IsWeakProxy(r)
        assert not IsWeakRef(r)

        r = weakref.ref(b)
        b2 = _Stub()
        r2 = weakref.ref(b2)
        assert r == r2
        assert hash(r) == hash(r2)

        r = GetWeakRef(b.Method)
        r2 = GetWeakRef(b.Method)
        assert r == r2
        assert hash(r) == hash(r2)

    def testGetRealObj(self):
        b = _Stub()
        r = GetWeakRef(b)
        assert GetRealObj(r) is b

        r = GetWeakRef(None)
        assert GetRealObj(r) is None

    def testGetWeakProxyFromWeakRef(self):
        b = _Stub()
        r = GetWeakRef(b)
        proxy = GetWeakProxy(r)
        assert IsWeakProxy(proxy)

    def testWeakSet(self):
        weak_set = WeakSet()
        s1 = _Stub()
        s2 = _Stub()

        weak_set.add(s1)
        assert isinstance(iter(weak_set).next(), _Stub)

        assert s1 in weak_set
        self.CustomAssertEqual(len(weak_set), 1)
        del s1
        self.CustomAssertEqual(len(weak_set), 0)

#         weak_set.add(s2)
#         self.CustomAssertEqual(len(weak_set), 1)
#         weak_set.remove(s2)
#         self.CustomAssertEqual(len(weak_set), 0)
#
#         weak_set.add(s2)
#         weak_set.clear()
#         self.CustomAssertEqual(len(weak_set), 0)
#
#         weak_set.add(s2)
#         weak_set.add(s2)
#         weak_set.add(s2)
#         self.CustomAssertEqual(len(weak_set), 1)
#         del s2
#         self.CustomAssertEqual(len(weak_set), 0)
#
#         # >>> Testing with FUNCTION
#
#         # Adding twice, having one
#         def function():
#             pass
#         weak_set.add(function)
#         weak_set.add(function)
#         self.CustomAssertEqual(len(weak_set), 1)

    def testRemove(self):
        weak_set = WeakSet()

        s1 = _Stub()

        self.CustomAssertEqual(len(weak_set), 0)

        # Trying remove, raises KeyError
        with pytest.raises(KeyError):
            weak_set.remove(s1)
        self.CustomAssertEqual(len(weak_set), 0)

        # Trying discard, no exception raised
        weak_set.discard(s1)
        self.CustomAssertEqual(len(weak_set), 0)

    def testWeakSet2(self):
        weak_set = WeakSet()

        # >>> Removing with DEL
        s1 = _Stub()
        weak_set.add(s1.Method)
        self.CustomAssertEqual(len(weak_set), 1)
        del s1
        self.CustomAssertEqual(len(weak_set), 0)

        # >>> Removing with REMOVE
        s2 = _Stub()
        weak_set.add(s2.Method)
        self.CustomAssertEqual(len(weak_set), 1)
        weak_set.remove(s2.Method)
        self.CustomAssertEqual(len(weak_set), 0)

    def testWithError(self):
        weak_set = WeakSet()

        # Not WITH, everything ok
        s1 = _Stub()
        weak_set.add(s1.Method)
        self.CustomAssertEqual(len(weak_set), 1)
        del s1
        self.CustomAssertEqual(len(weak_set), 0)

        # Using WITH, s2 is not deleted from weak_set
        s2 = _Stub()
        with pytest.raises(KeyError):
            raise KeyError('key')
        self.CustomAssertEqual(len(weak_set), 0)

        weak_set.add(s2.Method)
        self.CustomAssertEqual(len(weak_set), 1)
        del s2
        self.CustomAssertEqual(len(weak_set), 0)

    def testFunction(self):
        weak_set = WeakSet()

        def function():
            'Never called'

        # Adding twice, having one.
        weak_set.add(function)
        weak_set.add(function)
        self.CustomAssertEqual(len(weak_set), 1)

        # Removing function
        weak_set.remove(function)
        assert len(weak_set) == 0

    def CustomAssertEqual(self, a, b):
        '''
        Avoiding using "assert a == b" because it adds another reference to the ref-count.
        '''
        if a == b:
            pass
        else:
            assert False, "%s != %s" % (a, b)

    def SetupTestAttributes(self):

        class C(object):

            def f(self, y=0):
                return self.x + y

        class D(object):

            def f(self):
                'Never called'

        self.C = C
        self.c = C()
        self.c.x = 1
        self.d = D()

    def testCustomAssertEqual(self):
        with pytest.raises(AssertionError) as excinfo:
            self.CustomAssertEqual(1, 2)

        assert six.text_type(excinfo.value) == '1 != 2\nassert False'

    def testRefcount(self):
        self.SetupTestAttributes()

        # 2: one in self, and one as argument to getrefcount()
        self.CustomAssertEqual(sys.getrefcount(self.c), 2)
        cf = self.c.f
        self.CustomAssertEqual(sys.getrefcount(
            self.c), 3)  # 3: as above, plus cf
        rf = WeakMethodRef(self.c.f)
        pf = WeakMethodProxy(self.c.f)
        self.CustomAssertEqual(sys.getrefcount(self.c), 3)
        del cf
        self.CustomAssertEqual(sys.getrefcount(self.c), 2)
        rf2 = WeakMethodRef(self.c.f)
        self.CustomAssertEqual(sys.getrefcount(self.c), 2)
        del rf
        del rf2
        del pf
        self.CustomAssertEqual(sys.getrefcount(self.c), 2)

    def testDies(self):
        self.SetupTestAttributes()

        rf = WeakMethodRef(self.c.f)
        pf = WeakMethodProxy(self.c.f)
        assert not rf.is_dead()
        assert not pf.is_dead()
        assert rf()() == 1
        assert pf(2) == 3
        self.c = None
        assert rf.is_dead()
        assert pf.is_dead()
        assert rf() == None
        with pytest.raises(ReferenceError):
            pf()

    def testWorksWithFunctions(self):
        self.SetupTestAttributes()

        def foo(y):
            return y + 1
        rf = WeakMethodRef(foo)
        pf = WeakMethodProxy(foo)
        assert foo(1) == 2
        assert rf()(1) == 2
        assert pf(1) == 2
        assert not rf.is_dead()
        assert not pf.is_dead()

    def testWorksWithUnboundMethods(self):
        self.SetupTestAttributes()

        meth = self.C.f
        rf = WeakMethodRef(meth)
        pf = WeakMethodProxy(meth)
        assert meth(self.c) == 1
        assert rf()(self.c) == 1
        assert pf(self.c) == 1
        assert not rf.is_dead()
        assert not pf.is_dead()

    def testEq(self):
        self.SetupTestAttributes()

        rf1 = WeakMethodRef(self.c.f)
        rf2 = WeakMethodRef(self.c.f)
        assert rf1 == rf2
        rf3 = WeakMethodRef(self.d.f)
        assert rf1 != rf3
        del self.c
        assert rf1.is_dead()
        assert rf2.is_dead()
        assert rf1 == rf2

    def testProxyEq(self):
        self.SetupTestAttributes()

        pf1 = WeakMethodProxy(self.c.f)
        pf2 = WeakMethodProxy(self.c.f)
        pf3 = WeakMethodProxy(self.d.f)
        assert pf1 == pf2
        assert pf3 != pf2
        del self.c
        assert pf1 == pf2
        assert pf1.is_dead()
        assert pf2.is_dead()

    def testHash(self):
        self.SetupTestAttributes()

        r = WeakMethodRef(self.c.f)
        r2 = WeakMethodRef(self.c.f)
        assert r == r2
        h = hash(r)
        assert hash(r) == hash(r2)
        del self.c
        assert r() is None
        assert hash(r) == h

    def testRepr(self):
        self.SetupTestAttributes()

        r = WeakMethodRef(self.c.f)
        assert six.text_type(r)[:33] == '<WeakMethodRef to C.f for object '

        def Foo():
            'Never called'

        r = WeakMethodRef(Foo)
        assert six.text_type(r) == '<WeakMethodRef to Foo>'

    def testWeakList(self):
        weak_list = WeakList()
        s1 = _Stub()
        s2 = _Stub()

        weak_list.append(s1)
        assert isinstance(weak_list[0], _Stub)

        assert s1 in weak_list
        assert 1 == len(weak_list)
        del s1
        assert 0 == len(weak_list)

        weak_list.append(s2)
        assert 1 == len(weak_list)
        weak_list.remove(s2)
        assert 0 == len(weak_list)

        weak_list.append(s2)
        del weak_list[:]
        assert 0 == len(weak_list)

        weak_list.append(s2)
        del s2
        del weak_list[:]
        assert 0 == len(weak_list)

        s1 = _Stub()
        weak_list.append(s1)
        assert 1 == len(weak_list[:])

        del s1

        assert 0 == len(weak_list[:])

        def m1():
            'Never called'

        weak_list.append(m1)
        assert 1 == len(weak_list[:])
        del m1
        assert 0 == len(weak_list[:])

        s = _Stub()
        weak_list.append(s.Method)
        assert 1 == len(weak_list[:])
        s = weakref.ref(s)
        assert 0 == len(weak_list[:])
        assert s() is None

        s0 = _Stub()
        s1 = _Stub()
        weak_list.extend([s0, s1])
        assert len(weak_list) == 2

    def testSetItem(self):
        weak_list = WeakList()
        s1 = _Stub()
        s2 = _Stub()
        weak_list.append(s1)
        weak_list.append(s1)
        assert s1 == weak_list[0]
        weak_list[0] = s2
        assert s2 == weak_list[0]
