from __future__ import unicode_literals
"""
    @author
        ama@esss.com.br
        fabioz@esss.com.br
"""
import six



# Custom cache for optimization purposes.
__bases_cache = {}
__hierarchy_cache = {}

#===================================================================================================
# AllBasesNames
#===================================================================================================
def AllBasesNames(p_class):
    """
        :rtype: set with all the names of the bases classes of the given class.
    """
    try:
        return __bases_cache[p_class]
    except KeyError:
        result = set()
        for i_base in p_class.__bases__:
            result.add(i_base.__name__)
            result.update(AllBasesNames(i_base))
        return __bases_cache.setdefault(p_class, result)



#===================================================================================================
# IsInstance
#===================================================================================================
def IsInstance(p_object, p_class_name):
    """
    :param object p_object:
        The object we would like to test for.

    :param unicode p_class_name:
        Name or class to test if the object is an instance of.

    Like the built-in isinstance, but also accepts a class name as parameter.
    """
    try:
        # obtain the type of the class; using only type() is not enough, because some built-in
        # types don't respond to type() correctly (vtk objects for instance always return the
        # same type object)
        class_ = p_object.__class__
    except AttributeError:
        # some built-in objects don't have a __class__ attribute, but return its type correctly
        # from type()
        class_ = type(p_object)
    return IsSubclass(class_, p_class_name)


#===================================================================================================
# IsSubclass
#===================================================================================================
def IsSubclass(p_class, p_class_name):
    """
    Like the built-in issubclass, but also accepts a class name as parameter.
    """
    isins = isinstance  # put it in locals

    if isins(p_class_name, six.text_type):
        if p_class_name == p_class.__name__:
            return True

        try:
            names = __bases_cache[p_class]
        except KeyError:
            return p_class_name in AllBasesNames(p_class)
        else:
            return p_class_name in names


    elif isins(p_class_name, tuple) and len(p_class_name) > 0 and isins(p_class_name[0], six.text_type) :

        names = None

        for c in p_class_name:
            if c == p_class.__name__:
                return True

            if names is None:
                try:
                    names = __bases_cache[p_class]
                except KeyError:
                    names = AllBasesNames(p_class)

            if c in names:
                return True


        return False

    else:
        return issubclass(p_class, p_class_name)


#===================================================================================================
# _IterClassHierarchy
#===================================================================================================
def _IterClassHierarchy(class_):
    """
        Iterates through the whole hierarchy of a given class (including the class itself)
    """
    yield class_

    iter = _IterClassHierarchy
    for c in class_.__bases__:
        for c in iter(c):
            yield c


#===================================================================================================
# GetClassHierarchy
#===================================================================================================
def GetClassHierarchy(class_):
    """
        :rtype: the class hierarchy for a given class in a flattened way as a set.
    """
    try:
        return __hierarchy_cache[class_]
    except:
        return __hierarchy_cache.setdefault(class_, set(_IterClassHierarchy(class_)))


#===================================================================================================
# CheckOverridden
#===================================================================================================
def CheckOverridden(instance, current_method_class, method_name):
    """
    Checks if the current instance has overridden the given method from the passed class (to check
    if a method has a mandatory override).

    :param object instance:
        The instance we're checking.

    :param type current_method_class:
        The class we're checking for the override.

    :param unicode method_name:
        The name of the method to be overridden.

    :raises AssertionError:
        If the method is not overridden in a subclass.

    I.e.:

    class A(object):

        def method(self):
            CheckOverridden(self, A, 'method)

    class B(A):
        ...

    If B().method() is called in this case it'll throw an error.

    This is meant for non-abstract methods where the user usually overrides and calls super().
    """
    if instance.__class__ == current_method_class:
        return

    assert isinstance(instance, current_method_class), 'Expected %s to be a subclass of: %s' % (
        instance, current_method_class)

    from_instance = getattr(instance.__class__, method_name)
    from_class = getattr(current_method_class, method_name)

    if from_instance == from_class:
        assert instance.__class__ == current_method_class, \
            'The method %s should be overridden in %s' % (method_name, instance.__class__,)


