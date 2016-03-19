from __future__ import unicode_literals
from .is_frozen import IsFrozen
import os
import sys


class ModuleFinder(object):
    """
    This class converts python modules filenames into import like strings
    considering the current system path. If the given filename is not in the
    list of system-path an error is raised.

    This code was extracted from the TestRunner implementation so we can use it
    elsewhere (in the codegen_required_imports specifically)
    """

    def __init__(self, extend_sys_path=False, python_path=''):
        self.extend_sys_path = extend_sys_path
        self.python_path = self.ObtainPythonPath(python_path)

    @classmethod
    def ObtainPythonPath(cls, python_path=''):
        """
        Returns the python-path used by the module-finder considering the
        parameter and the sys.frozen attribute.
        """
        if isinstance(python_path, (list, tuple)):
            return python_path
        elif python_path:
            return python_path.split(os.pathsep)
        elif IsFrozen():
            return os.environ['PYTHONPATH'].split(os.pathsep)
        else:
            return sys.path

    def _FormatAsModuleName(self, p_filename, is_for_compare=False):
        """
        Convert the given filename to a "import path" (as expected by python's
        __import__)
        :param  is_for_compare:
            If true, make all lowercase so changes in the case does not affect
            comparations. The "PYTHONPATH" paths can contain paths that does
            not matches the case, but is still valid for win32 systems.
            Default is False.
        """
        result = p_filename
        result = result.replace('\\', '/')
        result = result.split('/')
        result = '.'.join(result)
        if is_for_compare and sys.platform == 'win32':
            result = result.lower()
        return result

    def ModuleName(self, filename, python_paths=None):
        """
        Given a module filename returns the module name for it considering the
        given system path.

        :param  filename:
            The filename of the python module

        :param  python_paths:
            A list of python path directories in import format.

        For example:
            x:\coilib50\source\python\coilib50\maestro ==> coilib50.maestro

            Considering that x:\coilib50\source\python is in PYTHONPATH
        """
        def MatchPath(p_path_a, p_path_b):
            if sys.platform == 'win32':
                return p_path_a.lower().startswith(p_path_b.lower())
            else:
                return p_path_a.startswith(p_path_b)

        def PythonPathCmp(p_path_a, p_path_b):
            # Longest paths have priority
            return len(p_path_b) - len(p_path_a)

        if python_paths is None:
            python_paths = self.SystemPath()

        result = self._FormatAsModuleName(os.path.splitext(filename)[0])

        for i_python_path in sorted(python_paths, cmp=PythonPathCmp):
            if MatchPath(result, i_python_path):
                import_dir_path = result[len(i_python_path) + 1:]
                return import_dir_path

        python_path = '\n   - '.join(['\n'] + sorted(python_paths))
        raise RuntimeError(
            'Python path not found for filename: %r (%s)\n'
            ' Python Path:%s'
            % (filename, result, python_path)
        )

    @classmethod
    def GetImports(cls, directory, out_filters=[]):
        """
        Lists imports made by python files found in the given directory.

        Directory will be scanned recursively

        :param unicode directory:
            Path to a directory

        :param list(unicode) out_filters:
            List of filename filters
            .. see:: FindFiles

        :rtype: list(unicode)
        :returns:
            List of module imported by python
        """
        from zerotk.easyfs import FindFiles
        from modulefinder import ModuleFinder as Finder

        finder = Finder(bytes(directory))
        for py_filename in FindFiles(
            directory,
            in_filters='*.py',
            out_filters=out_filters
        ):
            finder.run_script(py_filename)

        return map(unicode, sorted(finder.modules.keys() + finder.badmodules.keys()))

    @classmethod
    def GetMatchingImports(cls, path, regex_):
        """
        List projects in the given path matching the given regex..

        :param unicode path:
            A path to be searched recursively for imports

        :param unicode regex:
            A python regular expression to match each found import.
            Modules are recognized as ESSS projects if they match the regular expression

                '[a-zA-Z]+\d\d'

                Which means a sequence of letters followed by two numbers.

        :rtype: set(unicode)
        :returns:
            A set containing project names for all ESSS imports found in the given path

            e.g. set(['coilib50', 'sharedscripts10'])
        """

        def IsMatch(module_path, regex_):
            """
            Identifies if the given module_path represents a ESSS project (or application).

            Modules are recognized as ESSS projects if they match the regular expression
                [a-zA-Z]+\d\d

                Which means a sequence of letters followed by two numbers.

            :param unicode module_path:
                A module path in import format.
                Ex.:
                  coilib50.basic

            :rtype: unicode | None
            :returns:
                Returns the first part of the module if it is a esss module and None otherwise.
            """
            import re
            m = re.match(regex_, module_path)
            if m is None:
                return None
            return m.group(1)

        python_dir = path[:path.find('python') + len('python')]

        # List all modules imported in coilib50's python dir
        all_modules = cls.GetImports(python_dir, out_filters=[])

        # Filter modules that are ESSS projects
        result = set()
        for module in all_modules:
            m = IsMatch(module, regex_)
            if m is not None:
                result.add(m)
        return result

    def SystemPath(self, directories=()):
        """
        Returns the $PYTHONPATH in "module_name" format.

        Actually, returns the values found self.python_path, that may, or may not be $PYTHONPATH
        depending on how this class was constructed.

        :param list(unicode) directories:
            Included in the result IF self.extend_sys_path option is set (which is not the
            default).
        """
        result = [self._FormatAsModuleName(i, True) for i in self.python_path]
        if self.extend_sys_path:
            extend = map(os.path.abspath, directories)
            extend = [self._FormatAsModuleName(i, True) for i in extend]
            result = extend + result
        return result


def ImportModule(p_import_path):
    """
        Import the module in the given import path.

        * Returns the "final" module, so importing "coilib50.subject.visu" return the "visu"
        module, not the "coilib50" as returned by __import__
    """
    from zerotk.reraiseit import reraise
    try:
        result = __import__(p_import_path)
        for i in p_import_path.split('.')[1:]:
            try:
                result = getattr(result, i)
            except AttributeError as e:
                reraise(
                    e,
                    'AttributeError:  p_import_path: %s, %s has no %s' % (
                        p_import_path, result, i
                    )
                )
        return result
    except ImportError, e:
        reraise(e, 'Error importing module %s' % p_import_path)


def ImportToken(path):
    """
    The import token extends the functionality provided by ImportModule by importing members inside
    other members. This is useful to import constants, exceptions and enums wich are usually
    declared inside other module.

    """
    try:
        return ImportModule(path)
    except ImportError:
        try:
            mod, name = path.rsplit('.', 1)
        except ValueError:
            raise ImportError('Cannot import %s' % (path,))

        try:
            ret = ImportToken(mod)
        except ImportError:
            raise ImportError('Cannot import %s' % (path,))
        try:
            return getattr(ret, name)
        except AttributeError:
            raise ImportError('Cannot find %s in module: %s' % (ret, mod))
