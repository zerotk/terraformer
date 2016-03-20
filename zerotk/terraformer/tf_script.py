from __future__ import unicode_literals

from functools import partial
from io import StringIO

import six

from zerotk.clikit.app import App
from zerotk.easyfs import (
    EOL_STYLE_UNIX, FindFiles, GetFileLines, IsDir, StandardizePath)

app = App('terraformer')


# Valid extensions for fix-format.
EXTENSIONS = {
    '.py', '.cpp', '.c', '.h', '.hpp', '.hxx', '.cxx', '.java', '.js'
}

# Python extensions.
# This is overridden for test purposes.
PYTHON_EXT = '.py'


@app
def Symbols(console_, filename):
    """
    List all symbols in the given python source code. Currently only lists IMPORTS.

    :param filename: Python source code.
    """
    from zerotk.terraformer import TerraFormer

    terra = TerraFormer.Factory(filename)
    for i_import_symbol in sorted(terra.symbols, key=lambda x: (x.lineno, x.column, x.name)):
        console_.Print('%d: IMPORT %s' %
                       (i_import_symbol.lineno, i_import_symbol.name))


@app
def FixFormat(console_, refactor=None, python_only=False, single_job=False, sorted=False, inverted_refactor=False, *sources):
    """
    Perform the format fixes on sources files, including tabs, eol, eol-spaces and imports.

    Fix-format details:
        - tabs: Fix for tabs in the code. We always use spaces.
        - eol: Fix for EOL style. We use UNIX-EOL
        - eol-spaces: Fix for spaces in the end of the lines. We don't want them.
        - imports: Sort imports statements

    Local Imports Fix:
        Replaces global imports by local imports when the symbol is available locally.
        Ex.
            alpha/bravo/__init__.py:
                from zulu import ZuluClass

            alpha/bravo/module.py:
                from alpha.bravo import ZuluClass ==> from zulu import ZuluClass

        REQUIREMENT: The package must be available on python path.

    :param refactor: Refactor ini file mapping source imports to target imports.
    :param python_only: Only handle python sources (.py).
    :param single_job: Avoid using multithread (for testing purposes).
    :param sorted: Sort the output.
    :param inverted_refactor: Invert refactor names and values loaded from refactor file.
    :param sources: Source directories or files.
    """
    from functools import partial

    def GetRefactorDict(refactor_filename, inverted):
        from zerotk.terraformer.string_dict_io import StringDictIO

        result = None
        if refactor is not None:
            result = StringDictIO.Load(refactor_filename, inverted=inverted)
        return result

    extensions = _GetExtensions(python_only)
    filenames = _GetFilenames(sources, extensions)
    refactor = GetRefactorDict(refactor, inverted_refactor)
    partial_fix_format = partial(_FixFormat, refactor=refactor)
    _Map(console_, partial_fix_format, filenames, sorted, True)


@app
def AddImportSymbol(console_, import_symbol, single_job=False, *sources):
    """
    Adds an import-symbol in all files.

    The import statement is added in the first line of the code, before comments but after module
    string docs.

    :param sources: Source directories or files.
    :param import_symbol: The symbol to import. Ex. "__future__.unicode_literals"
    :param single_job: Avoid using multithread (for testing purposes).
    """
    filenames = _GetFilenames(sources, [PYTHON_EXT])
    partial_add_import_symbol = partial(
        _AddImportSymbol, import_symbol=import_symbol)
    _Map(console_, partial_add_import_symbol, filenames, sorted, True)


@app
def FixCommit(console_, source, single_job=False):
    """
    Perform the format fixes on sources files on a git repository modified files.

    :param source: A local git repository working directory.
    :param single_job: Avoid using multithread (for testing purposes).
    """

    def GetFilenames(cwd):
        from gitit.git import Git

        git = Git.GetSingleton()

        working_dir = git.GetWorkingDir(cwd)
        staged_filenames = git.Execute(
            'diff --name-only --diff-filter=ACM --staged', repo_path=working_dir)
        changed_filenames = git.Execute(
            'diff --name-only --diff-filter=ACM', repo_path=working_dir)

        r_filenames = staged_filenames + changed_filenames
        r_filenames = set(r_filenames)
        r_filenames = sorted(r_filenames)
        r_filenames = _FilterFilenames(r_filenames)
        r_filenames = [working_dir + '/' + i for i in r_filenames]
        return r_filenames

    filenames = GetFilenames(source)
    partial_fix_format = partial(_FixFormat, refactor={})
    _Map(console_, partial_fix_format, filenames, sorted, True)


@app
def FixIsFrozen(console_, *sources):
    """
    Fix some pre-determinated set of symbols usage with the format:

        <module>.<symbol>

    Eg.:
        from coilib50.basic import property
        property.Create
        ---
        from ben10 import property_
        property_.Create

    This was necessary for BEN-30. Today TerraFormer only acts on import-statements. We have plans
    to also act on imported symbols usage.

    :param sources: List of directories or files to process.
    """
    from zerotk.easyfs import CreateFile, EOL_STYLE_UNIX, FindFiles, GetFileContents

    FIND_REPLACE = [
        ('StringIO', 'StringIO', 'from io import StringIO'),
        ('cStringIO', 'StringIO', 'from io import StringIO'),
        ('coilib50.IsFrozen', 'IsFrozen',
         'from ben10.foundation.is_frozen import IsFrozen'),
        ('coilib50.IsDevelopment', 'IsDevelopment',
         'from ben10.foundation.is_frozen import IsDevelopment'),
        ('coilib50.SetIsFrozen', 'SetIsFrozen',
         'from ben10.foundation.is_frozen import SetIsFrozen'),
        ('coilib50.SetIsDevelopment', 'SetIsDevelopment',
         'from ben10.foundation.is_frozen import SetIsDevelopment'),
        ('coilib40.basic.IsInstance', 'IsInstance',
         'from ben10.foundation.klass import IsInstance'),
    ]

    PROPERTY_MODULE_SYMBOLS = [
        'PropertiesDescriptor',
        'Property',
        'Create',
        'CreateDeprecatedProperties',
        'CreateForwardProperties',
        'FromCamelCase',
        'MakeGetName',
        'MakeSetGetName',
        'MakeSetName',
        'ToCamelCase',
        'Copy',
        'DeepCopy',
        'Eq',
        'PropertiesStr',
    ]
    for i_symbol in PROPERTY_MODULE_SYMBOLS:
        FIND_REPLACE.append(
            ('property.%s' % i_symbol, 'property_.%s' %
             i_symbol, 'from ben10 import property_'),
        )

    for i_filename in _GetFilenames(sources, [PYTHON_EXT]):
        contents = GetFileContents(i_filename)
        imports = set()
        for i_find, i_replace, i_import in FIND_REPLACE:
            if i_find in contents:
                contents = contents.replace(i_find, i_replace)
                imports.add(i_import)

        if imports:
            console_.Item(i_filename)
            lines = contents.split('\n')
            index = None
            top_doc = False
            for i, i_line in enumerate(lines):
                if i == 0:
                    for i_top_doc in ("'''", '"""'):
                        if i_top_doc in i_line:
                            console_.Print('TOPDOC START: %d' % i, indent=1)
                            top_doc = i_top_doc
                            break
                    continue
                elif top_doc:
                    if i_top_doc in i_line:
                        console_.Print('TOPDOC END: %d' % i, indent=1)
                        index = i + 1
                        break
                    continue

                elif i_line.startswith('import ') or i_line.startswith('from '):
                    index = i - 1
                    break

                elif i_line.strip() == '':
                    continue

                console_.Print('ELSE: %d: %s' % (i, i_line))
                index = i
                break

            assert index is not None
            lines = lines[0:index] + list(imports) + lines[index:]
            contents = '\n'.join(lines)
            CreateFile(
                i_filename,
                contents,
                eol_style=EOL_STYLE_UNIX,
                encoding='UTF-8'
            )


@app
def FixEncoding(console_, *sources):
    """
    Fix python module files encoding, converting all non-ascii encoded files to UTF-8.

    :param sources: List of directories or files to process.
    """
    from zerotk.easyfs import CreateFile, GetFileContents
    import io

    def GetPythonEncoding(filename):
        import re

        # Read the file contents in a encoding agnostic way, after all we're
        # trying to find out the file encoding.
        with open(filename, mode='rb') as iss:
            for i, i_line in enumerate(iss.readlines()):
                if i > 10:
                    # Only searches the first lines for encoding information.
                    break
                r = re.match(b'#.*coding[:=] *([\w\-\d]*)', i_line)
                if r is not None:
                    return i, r.group(1)
        return 0, None

    for i_filename in _GetFilenames(sources, [PYTHON_EXT]):
        try:
            # Try to open using ASCII. If it fails means that we have a
            # non-ascii file.
            with io.open(i_filename, encoding='ascii') as iss:
                iss.read()
        except UnicodeDecodeError:
            try:
                line_no, encoding = GetPythonEncoding(i_filename)
                if encoding is None:
                    console_.Print(
                        '%s: <red>UKNOWN</r> Please configure the file coding.' % i_filename)
                    continue
                console_.Item('%s: %s (line:%s)' %
                              (i_filename, encoding, line_no))
                lines = GetFileContents(
                    i_filename, encoding=encoding).split('\n')
                del lines[line_no]
                lines = ['# coding: UTF-8'] + lines
                contents = '\n'.join(lines)
                CreateFile(i_filename, contents, encoding='UTF-8',
                           eol_style=EOL_STYLE_UNIX)
            except:
                console_.Print('<red>%s: ERROR</>' % i_filename)
                raise


@app
def FixStringio(console_, *sources):
    """
    Fix StringIO usage.

    :param sources: List of directories or files to process.
    """
    from terraformer import FileTooBigError, TerraFormer

    for i_filename in _GetFilenames(sources, [PYTHON_EXT]):
        try:
            terra = TerraFormer(filename=i_filename)
            changed = terra.ReorganizeImports(
                refactor={
                    'StringIO.StringIO': 'from io.StringIO',
                    'cStringIO.StringIO': 'from io.StringIO',
                    'cStringIO': 'from io.StringIO',
                    'StringIO': 'from io.StringIO',
                }
            )
            if changed:
                console_.Item('%s: FIXED' % i_filename)
                for i_symbol in terra.module.Walk():
                    if i_symbol.PREFIX == 'USE' and i_symbol.name in ('cStringIO.StringIO', 'StringIO.StringIO'):
                        i_symbol.Rename('StringIO')
                terra.Save()
        except FileTooBigError:
            console_.Item('%s: FileTooBig (for TerraFormer)' % i_filename)


def _GetFilenames(paths, extensions):
    """
    Lists filenames matching the given paths and extensions.

    :param paths:
        List of paths or filenames to match.
    :param extensions:
        List of extensions to match. Ex.: .py, .cpp.
    :return list:
        Returns a list of matching paths.
    """
    result = []
    for i_path in paths:
        if IsDir(i_path):
            extensions = ['*%s' % i for i in extensions]
            result += FindFiles(i_path, extensions)
        else:
            result += [i_path]
    result = map(StandardizePath, result)
    return result


def _reorganize_imports(filename, refactor={}):
    """
    Reorganizes all import statements in the given filename, optionally performing a "move"
    refactoring.

    This is the main API for TerraForming.

    :param unicode filename:
        The file to perform the reorganization/refactoring. Note that the file is always
        rewritten by this algorithm, no backups. It's assumed that you're using a version
        control system.

    :param dict refactor:
        A dictionary mapping the moved symbols path. The keys are the current path, the values
        are the new path.
        Ex:
            {
                'coilbi50.basic.Bunch' : 'etk11.foundation.bunch.Bunch',
                'coilbi50.basic.interfaces' : 'etk11.interfaces',
            }

        Note that we do not support symbol renaming, only move. This means that the last part of
        the string must be the same. In the example, "Bunch" and "interface".

    :return boolean:
        Returns True if the file was changed.
    """
    from zerotk.terraformer import TerraFormer
    from zerotk.reraiseit import reraise

    try:
        terra = TerraFormer.Factory(filename)
        terra.ReorganizeImports(refactor=refactor)
        changed = terra.Save()
        return changed
    except Exception as e:
        reraise(e, 'On TerraForming.ReorganizeImports with filename: %s' % filename)


def _FixFormat(filename, refactor):
    """
    Perform the operation in a multi-threading friendly global function.

    The operation is to perform format fixes in the given python source code.
    """
    from zerotk.terraformer.print_detailed_traceback import PrintDetailedTraceback

    try:
        changed = False
        if filename.endswith(PYTHON_EXT):
            changed = _reorganize_imports(filename, refactor=refactor)
    except Exception as e:
        oss = StringIO()
        PrintDetailedTraceback(stream=oss)
        result = (
            '- %s: ERROR:\n  %s\n--- * ---\n%s' % (
                filename, e, oss.getvalue()
            ),
            0
        )
    else:
        if changed:
            result = ('- %s: FIXED' % filename, 1)
        else:
            result = ('- %s: skipped' % filename, 2)
    return result


def _AddImportSymbol(filename, import_symbol):
    """
    Perform the operation in a multi-threading friendly global function.

    The operation is add a import-symbol to a filename.
    """
    from zerotk.terraformer import TerraFormer

    terra = TerraFormer.Factory(filename)
    terra.AddImportSymbol(import_symbol)
    terra.ReorganizeImports()
    changed = terra.Save()

    if changed:
        result = '- %s: FIXED' % filename
    else:
        result = '- %s: skipped' % filename

    return result


def _FilterFilenames(filenames, extensions=EXTENSIONS):
    """
    Filters the given filenames that don't match the given extensions.

    :param list(str) filenames:
        List of filenames.

    :param list(str) extensions:
        List of extensions.

    :return:
        List of filename.
    """
    import os

    if extensions is None:
        return filenames
    else:
        return [
            i for i in filenames
            if os.path.splitext(i)[1] in extensions
        ]


def _GetExtensions(python_only):
    """
    Returns a list of extensions based on command line options.

    :param bool python_only:
        Command line option to consider only python files.

    :return list(str):
        List of extensions selected by the user.
    """
    if python_only:
        return {PYTHON_EXT}
    else:
        return EXTENSIONS


def _Map(console_, func, func_params, _sorted, single_job):
    """
    Executes func in parallel considering some options.

    :param callable func:
        The function to call.

    :param list func_params:
        List of parameters to execute the function with.

    :param _sorted:
        Sorts the output.

    :param single_job:
        Do not use multiprocessing algorithm.
        This is used for debug purposes.
    :return:
    """

    if single_job:
        imap = six.moves.map
    else:
        import concurrent.futures
        executor = concurrent.futures.ProcessPoolExecutor()
        imap = executor.map

    output = []
    for i_result in imap(func, func_params):
        if isinstance(i_result, tuple):
            text, verbosity = i_result
        else:
            text = i_result
            verbosity = 1
        if _sorted:
            output.append(text)
        else:
            console_.Print(text, verbosity=verbosity)

    for i_output_line in sorted(output):
        console_.Print(i_output_line)
