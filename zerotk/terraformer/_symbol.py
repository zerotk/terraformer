from __future__ import unicode_literals

import os

from .decorators import Comparable, Override


class Symbol(object):
    """
    Represents a python symbol definition.
    This is also the base class for other kinds of symbols.
    """

    PREFIX = 'DEF'

    def __init__(self, parent, name, code, code_replace=None):
        from lib2to3.pytree import Leaf, Node
        from ._lib2to3 import GetNodePosition
        from types import NoneType

        self.name = name

        assert isinstance(code, (Node, Leaf, NoneType))
        self.code = code
        self.code_replace = code_replace
        self.lineno = 0
        self.column = 0
        if self.code:
            self.lineno, self.column = GetNodePosition(self.code)

        # Tree structure
        self.parent = None
        self._children = []
        self.SetParent(parent)

    def SetParent(self, parent):
        if self.parent:
            self.RemoveFromParent()
        self.parent = parent
        if self.parent:
            self.parent._children.append(self)

    def RemoveFromParent(self):
        for i, i_child in enumerate(self.parent._children):
            if i_child is self:
                del self.parent._children[i]
                self.parent = None
                return True
        return False

    def _AsString(self):
        return '%s (%d, %d) %s' % (self.PREFIX, self.lineno, self.column, self.name)

    def AsString(self, indent=0):
        indentation = '  ' * indent
        result = [indentation + self._AsString()]
        for i_child in self._children:
            result.append(i_child.AsString(indent + 1))
        return '\n'.join(result)

    def __str__(self):
        return self.AsString()

    def HandleArgs(self, args, nodes):
        for i_arg in args:
            if isinstance(i_arg, tuple):
                self.HandleArgs(i_arg, nodes)
            else:
                SymbolArgument(self, i_arg.value, i_arg)

    def CreateCode(self, indent, page_width):
        """
        Create a lib2to3 code for this symbol.

        For now only import-block related symbols have this implemented, but later we'll have more
        of these.

        :param int indent:
            The indentation of the code. This is counted as the number of spaces, so for our
            standards this should be multiple of 4.

        :param int page_width:
            The generated code will have at most this width (in characters).

        :return list(lib2to3.Node):
        """
        raise NotImplementedError()

    def Walk(self):
        """
        Iterates over the symbols.

        :return iter(Symbol):
        """
        yield self
        for i_child in self._children:
            for j_child in i_child.Walk():
                yield j_child

    @classmethod
    def _InsertCodeBeforeNode(cls, node, code):

        if not node.parent:
            raise TypeError(
                "Can't insert before node that doesn't have a parent.")

        if not isinstance(code, list):
            code = [code]

        pos = node.parent.children.index(node)
        new_children = []
        for i, i_child in enumerate(node.parent.children):
            if i == pos:
                new_children += code
            new_children.append(i_child)

        for j_node in code:
            j_node.parent = node.parent
        node.parent.children = new_children
        node.parent.changed()


#=========================================================================
# Scope
#=========================================================================
class Scope(Symbol):
    """
    Represents a python scope.
    Symbols that define a scope derive from this class (Eg.: method, class), giving it a prefix.
    """

    def __init__(self, parent, name, code, code_replace=None):
        Symbol.__init__(self, parent, name, code, code_replace=code_replace)

        self.nested = False

    def AddSymbolUsage(self, symbol, code, code_replace=None):
        return SymbolUsage(self, symbol, code, code_replace=code_replace)

    def AddSymbolDefinition(self, symbol, code):
        return Symbol(self, symbol, code)


class SymbolArgument(Symbol):
    """
    Represents a argument symbol definition.
    """

    PREFIX = 'ARG'


class SymbolUsage(Symbol):
    """
    Represents a symbol usage.

    Later on we'll link each symbol-usage with the declaration it refers, either a import symbol or
    a locally defined symbol such as a class, method or variable.
    """

    PREFIX = 'USE'

    def Rename(self, symbol):
        from lib2to3.fixer_util import Name
        node = Name(symbol, self.code.prefix)
        self._InsertCodeBeforeNode(self.code, node)
        for i_node in self.code_replace:
            i_node.remove()


#=========================================================================
# ImportSymbol
#=========================================================================
@Comparable
class ImportSymbol(Symbol):
    """
    Represents an import symbol.

    Examples:
        import alpha
        from alpha import Alpha
        from alpha import Alpha as MyAlpha

    :cvar str symbol:
        The symbol being imported.

    :cvar KIND_IMPORT_XXX kind:
        Either import-name (import XXX) or import-from (from XXX import YYY)

    :cvar str import_as:
        Optional rename of the import (import XXX as YYY)
    """

    PREFIX = 'IMPORT'

    KIND_IMPORT_NAME = 298
    KIND_IMPORT_FROM = 297

    def __init__(self, parent, name, import_as=None, comment='', kind=KIND_IMPORT_NAME, lineno=0):
        """
        :param str symbol:
            The import-symbol.

        :param str|None import_as:
            Optional alias for the symbol.

        :param str comment:
            A comment associated with the import
            Ex. # @UnusedImport

        :param KIND_IMPORT_XXX kind:
            The kind of import.
        """
        assert isinstance(name, (str, unicode))
        assert isinstance(comment, (str, unicode))
        assert kind in (self.KIND_IMPORT_NAME, self.KIND_IMPORT_FROM)
        Symbol.__init__(self, parent, name, None)

        self.import_as = import_as
        self.comment = comment
        self.lineno = lineno

        if '.' not in name and kind == self.KIND_IMPORT_FROM:
            kind = self.KIND_IMPORT_NAME
        self.kind = kind

    def __repr__(self):
        return '<ImportSymbol "%s">' % self.name

    def Copy(self, parent=None, name=None):
        """
        Creates a copy of this instance, optionally replacing some attributes with the given ones.

        :param parent:
            If not None, uses this value instead of the instance's attribute as the copy parent.

        :param name:
            If not None, uses this value instead of the instance's attribute as the copy name.

        :return ImportSymbol:
        """
        return self.__class__(
            parent or self.parent,
            name or self.name,
            self.import_as,
            self.comment,
            self.kind,
            self.lineno,
        )

    def GetPackageName(self):
        """
        Returns the import-symbol prefix.

        This is only valid for import-symbols of type import-from, in which case it returns
        the "from" part of the import. Returns None if kind is import-name.

        Example:
            >s = ImportSymbol("Alpha", 'alpha')  # from alpha import Alpha
            >s.GetPackageName()
            'alpha'

        :return str:
        """
        if self.kind == self.KIND_IMPORT_FROM:
            assert '.' in self.name
            return self.name.rsplit('.', 1)[0]
        else:
            return None

    def GetToken(self):
        """
        Returns the import token of a import-symbol of kind import-from.
        Returns the symbol if kind is import-name.

        :return str:
        """
        if self.kind == self.KIND_IMPORT_FROM:
            assert '.' in self.name, "ERROR: Import-symbol 'from' has no dot in it: \"%s\"" % self.name
            return self.name.rsplit('.', 1)[1]
        else:
            return self.name

    def _cmpkey(self):
        """
        Implements @Comparable._cmpkey.

        Make sure that
        """
        index = 0
        if self.name.startswith('_'):
            index = -1
        elif '@terraforming:last-import' in self.comment or '@terraformer:last-import' in self.comment:
            index = 1
        return index, self.name

    def CreateNameNode(self, prefix=' '):
        """
        Creates a lib2to3.Node containing the name part of the import-symbol.
        This is REused by CreateCode implementation for this class and the "ImportFromScope."

        :param str prefix:
            The node prefix.

        :return lib2to3.Node:
        """
        from lib2to3 import pygram
        from lib2to3.fixer_util import Name
        from lib2to3.pytree import Node

        if self.import_as is not None:
            return Node(
                pygram.python_symbols.import_as_name,
                [
                    Name(self.GetToken(), prefix=prefix),
                    Name('as', prefix=' '),
                    Name(self.import_as, prefix=' ')
                ]
            )
        else:
            return Name(self.GetToken(), prefix=prefix)

    @Override(Symbol.CreateCode)
    def CreateCode(self, indent, page_width):
        from lib2to3 import pygram
        from lib2to3.fixer_util import Name, Newline
        from lib2to3.pytree import Node

        assert self.kind == self.KIND_IMPORT_NAME

        name_node = self.CreateNameNode()
        new_line = Newline()
        new_line.prefix = self.comment
        result = Node(
            pygram.python_symbols.simple_stmt,
            prefix=' ' * indent,
            children=[Name('import'), name_node, new_line]
        )
        return [result]


#=========================================================================
# ImportFromScope
#=========================================================================
@Comparable
class ImportFromScope(Scope):
    """
    We're representing a import-from import as a scope that contains import-symbols as child
    symbols.

    This interpretation makes it easier to rename a package (alpha to bravo) that imports many
    symbols.

    Eg.:
        from alpha import Bravo, Charlie
        ---
        form bravo import Bravo, Charlie

    But this also makes it difficult to rename symbols and end in different packages (bravo,
    charlie).

    Eg.:
        from alpha import Bravo, Charlie
        ---
        form bravo import Bravo
        from charlie import Charlie
    """

    PREFIX = 'IMPORT-FROM'

    def Copy(self, name):
        """
        Creates a copy of this instance, optionally replacing some attributes with the given ones.

        :param name:
            If not None, uses this value instead of the instance's attribute as the copy name.

        :return ImportFromScope:
        """

        result = self.__class__(
            self.parent,
            name or self.name,
            self.code,
        )
        for i_child in self._children:
            i_child.Copy(parent=result)
        return result

    def _cmpkey(self):
        """
        Implements Comparable._cmpkey.
        """
        index = -100
        if self.name.startswith('_'):
            index = -101
        return index, self.name

    @Override(Symbol.CreateCode)
    def CreateCode(self, indent, page_width):
        from lib2to3 import pygram
        from lib2to3.fixer_util import Name, Newline
        from lib2to3.pytree import Node

        def _CreateCode(indent, package, symbols, comment):
            """
            Create code:
                from <package> import <symbols> # <comment>
            """
            # children: the children nodes for the final from-import statement
            children = [
                Name('from', prefix=' ' * indent),
                Name(package, prefix=' '),
                Name('import', prefix=' '),
            ]

            # name_leaf: list of leaf nodes with the symbols to import
            name_leafs = []
            symbols = sorted(symbols)
            for i, i_symbol in enumerate(symbols):
                prefix = ' ' if i == 0 else ', '
                name_leafs.append(i_symbol.CreateNameNode(prefix))

            # nodes_wrap: if true, we need to wrap the import statement
            nodes_wrap = False
            line_len = 0
            line_len += reduce(lambda x, y: x + y,
                               map(len, map(str, children)), 0)
            line_len += reduce(lambda x, y: x + y,
                               map(len, map(str, name_leafs)), 0)
            if line_len > page_width:
                # Add parenthesis around the "from" names
                name_leafs[0].prefix = ''
                name_leafs.insert(0, Name('(', prefix=' '))
                name_leafs.append(Name(')'))
                nodes_wrap = True

            # Adds the name_leafs to the children list
            children += [Node(pygram.python_symbols.import_as_names, name_leafs)]

            # from_import: the final node for the import statement
            from_import = Node(pygram.python_symbols.import_from, children)

            # result: a simple-statement node with the import statement and
            # EOL.
            new_line = Newline()
            new_line.prefix = comment
            result = Node(
                pygram.python_symbols.simple_stmt,
                children=[
                    from_import,
                    new_line,
                ],
            )

            # Wrap nodes if necessary (see nodes_wrap above)
            if nodes_wrap:
                ImportBlock.TextWrapForNode(result, page_width, indent)

            return result

        # Use some criteria to separate this import-from-package children into many statements:
        # * has_star: "from XXX import *" must be alone in a line.
        # * comment: inline comments must be preserved for each different statement.
        groups = {}
        for i_child in self._children:
            has_star = i_child.name.endswith('*')
            key = has_star, i_child.comment
            groups.setdefault(key, []).append(i_child)

        result = []
        for (_has_star, i_comment), i_symbols in sorted(groups.iteritems()):
            node = _CreateCode(indent, self.name, i_symbols, i_comment)
            result.append(node)

        return result


#=========================================================================
# ClassScope
#=========================================================================
class ClassScope(Scope):
    """
    Represents a class symbol declaration, which also declares a scope.
    """

    PREFIX = 'class'


#=========================================================================
# FunctionScope
#=========================================================================
class FunctionScope(Scope):
    """
    Represents a function symbol declaration, which also declares a scope.
    """

    PREFIX = 'def'


#=========================================================================
# ModuleScope
#=========================================================================
class ModuleScope(Scope):
    """
    Represents a module declaration, which also declares a scope.
    """

    PREFIX = 'module'


#=========================================================================
# ImportBlock
#=========================================================================
class ImportBlock(Scope):
    """
    A import-block is a semantic scope created here in order to group import-statements together for
    reorganizing and refactoring algorithms.
    """

    PREFIX = 'IMPORT-BLOCK'

    PYTHON_EXT = '.py'

    def __init__(self, parent, code, code_replace, id, lineno, indent):
        Scope.__init__(self, parent, 'import-block #%d' %
                       id, code, code_replace=code_replace)
        self.id = id

    def Refactor(self, refactor={}):
        """
        Perform the refactor for this import-block, renaming all children import-statements using
        the given refactor dictionary.

        :param dict(str,str) refactor:
            Maps old symbols to their new values.
            * Suffix the old symbol name with '$' if you want it in the end of the symbol.
            * Prefix the new value with "from " to force "import-from" syntax even if the symbol
              was originally imported as an "import-name".
        """
        for i_import_symbol in [i for i in self._WalkImportSymbols()]:
            new_name = refactor.get(i_import_symbol.name)
            if new_name is None:
                new_name = refactor.get(i_import_symbol.name + '$')
                if new_name is None:
                    new_package = refactor.get(
                        i_import_symbol.GetPackageName())
                    if new_package is not None:
                        new_name = new_package + '.' + i_import_symbol.GetToken()

            if new_name:
                if new_name.startswith('from '):
                    kind = i_import_symbol.KIND_IMPORT_FROM
                    new_name = new_name[5:]
                else:
                    kind = i_import_symbol.kind

                self.ObtainImportSymbol(
                    new_name,
                    import_as=i_import_symbol.import_as,
                    comment=i_import_symbol.comment,
                    kind=kind,
                    lineno=i_import_symbol.lineno,
                )
                i_import_symbol.RemoveFromParent()

    def FixLocalSymbols(self, filename):
        """
        Tries to rename some imports to use local symbols if they are available.

        This is necessary to avoid import loops in the following conditions:

        * Module importing module in the same package
        * The package (__init__.py) imports both symbols

            Ex.:
            /alpha/
                __init__.py
                [
                    from bravo import *
                    from charlie import *
                ]
                bravo.py
                [
                    import alpha.charlie
                ]
                charlie.py

        We solve this by:

        * Imports in the above conditions must be local, not global.
            Ex.:
                bravo.py
                [
                    import charlie
                ]

        :param str filename:
        :return:
        """

        def LocalImportRename(import_symbol, filename):
            """
            Converts the given import-symbol into a local import.

            Terms:
                * working: meaning the module we are working one. The import-symbol and filename given as parameters.
                * init: refers to package (__init__.py)
                * local: refers to the module, found in the same location the "working" module, that contains a symbol
                  used by the working symbol.
            """
            from ._terra_former import TerraFormer

            # CASE: Renaming the symbol is ignored because we don't want to change the code.
            # IDEA: We could change only the "left" side of the import leaving
            # the rename intact.
            if import_symbol.import_as:
                return

            if '__init__.py' in filename:
                # CASE: This is a __init__ file already.
                return

            working_package = import_symbol.GetPackageName()
            if working_package is None:
                # CASE: A name import, such as "import ben10"
                return

            working_token = import_symbol.GetToken()

            if working_token == '*':
                # CASE: Importing all symbols from a module/package. This case
                # is ignored.
                return

            # Obtain the package __init__.py filename
            package_filename = os.path.abspath(os.path.dirname(filename))
            package_filename += '/__init__' + self.PYTHON_EXT
            if not os.path.isfile(package_filename):
                return

            # CASE: The symbol is not available in the package
            package_terra_former = TerraFormer.Factory(package_filename)
            init_package_name = package_terra_former.GetModuleName()
            if init_package_name is None:
                return

            # CASE: The symbol matches one found in the package, but it is from
            # another package, not this one.
            if import_symbol.GetPackageName() != init_package_name:
                return

            # CASE: Finally, we found that we are importing a symbol available in a local module using a global import.
            # In this case we fix it using the same local import as the package
            # __init__.py is using.
            result = package_terra_former.GetSymbolFromToken(working_token)
            if result is None:
                return

            return result.name

        for i_import_symbol in [i for i in self._WalkImportSymbols()]:
            new_name = LocalImportRename(i_import_symbol, filename)

            if new_name:
                self.ObtainImportSymbol(
                    new_name,
                    import_as=i_import_symbol.import_as,
                    comment=i_import_symbol.comment,
                    kind=i_import_symbol.kind,
                    lineno=i_import_symbol.lineno,
                )
                i_import_symbol.RemoveFromParent()

    def _WalkImportSymbols(self):
        """
        Iterator for import-symbols.

        :return iter(ImportSymbol):
        """
        for i_child in self._children:
            if isinstance(i_child, ImportSymbol):
                yield i_child
            elif isinstance(i_child, ImportFromScope):
                for j_child in i_child._children:
                    assert isinstance(j_child, ImportSymbol)
                    yield j_child
            else:
                raise TypeError()

    def Reorganize(self, page_width=100, refactor={}, filename=None):
        """
        Reorganize the import-statements replacing the previous code by brand new import-statements.

        :param int page_width:
        :param dict refactor:
        :param str filename:
        :return:
        """
        if self._children:

            if refactor:
                self.Refactor(refactor)
            if filename:
                self.FixLocalSymbols(filename)

            symbol_imports = self._children

            # Create new nodes with all the import-statements.
            nodes = self.CreateCode(
                symbol_imports,
                self.column,
                page_width=page_width,
                filename=filename,
            )

            # Some extra fixes on new created nodes.
            if self.code_replace:
                assert len(nodes) > 0
                assert len(self.code_replace) > 0

                # Copies the prefix from the replaced code.
                nodes[0].prefix = self.code_replace[0].prefix

                # Remove EOL from new nodes under certain conditions:
                next_node = self.code_replace[-1].next_sibling
                if next_node and next_node.value == ';':
                    del nodes[-1].children[-1]

            # Insert new nodes before the marked position.
            self._InsertCodeBeforeNode(self.code, nodes)

            # Delete the code this code block replaces.
            for i_node in self.code_replace:
                i_node.remove()

            self.code = nodes[0]
            self.code_replace = nodes
        else:
            for i_node in self.code_replace:
                i_node.remove()

    def ObtainImportFromScope(self, name):
        """
        Returns an ImportFromScope associated with the given name, creating one if necessary.

        :param str name:
        :return ImportFromScope:
        """
        result = ImportFromScope(None, name, None)
        try:
            index = self._children.index(result)
        except ValueError:
            result.SetParent(self)
        else:
            result = self._children[index]
        return result

    def ObtainImportSymbol(
        self,
        name,
        import_as=None,
        comment='',
        kind=ImportSymbol.KIND_IMPORT_NAME,
        lineno=0
    ):
        result = ImportSymbol(None, name, import_as, comment, kind, lineno)
        package = result.GetPackageName()

        if kind == ImportSymbol.KIND_IMPORT_FROM and package is not None:
            parent = self.ObtainImportFromScope(package)
        else:
            parent = self

        try:
            index = parent._children.index(result)
        except ValueError:
            result.SetParent(parent)
        else:
            result = parent._children[index]
        return result

    def CreateCode(self, symbols, indent, page_width, filename=None):
        """
        Create lib2to3 nodes from the internal information.

        :param int page_width:
            The algorithm tries to respect this page-width for all statements.

        :param str filename:
            The name of the module we're working on.
            This is necessary for the local-imports algorithm.
        """
        result = []
        for i_symbol in sorted(symbols):
            result += i_symbol.CreateCode(indent, page_width)
        return result

    @classmethod
    def _WalkLeafs(cls, node):
        from lib2to3.pytree import Leaf

        if isinstance(node, Leaf):
            yield node
        else:
            for i_child in node.children:
                for j_leaf in cls._WalkLeafs(i_child):
                    yield j_leaf

    @classmethod
    def TextWrapForNode(cls, node, max_width, indent, start_at='(', end_at=')'):
        """
        Wrap the given node so it fits in max-width.

        Changes the nodes in-place.

        :param lib2to3.pytree.Node:
            Return a simple_stmt parser-node with the import statement code..Node node:

        :param int max_width:
            The number of columns to wrap the text.

        :param int indent:
            The text indentation in number of characters, not in number of "tabs".

        :param str start_at:
            The value of the node to enable the wrapping.
            Some lines should no be broken until a given symbol such as open parenthesis.

        :param str end_at:
            The value of the node to disable the wrapping.
        """
        started = False
        cumulative_len = 0
        symbols_count = 0
        for i_leaf in cls._WalkLeafs(node):
            # TODO: BEN-28: [terraformer] Consider the EOL prefix in the
            # cumulative_len, since it can contain comments
            if i_leaf.value == '\n':
                break

            if not started:
                leaf_len = len(str(i_leaf))
                cumulative_len += leaf_len
                started = i_leaf.value == start_at
            elif i_leaf.value == end_at:
                break
            else:
                symbols_count += 1

                if i_leaf.prefix not in (', ', ',\n', '\n', ' ', ''):
                    raise NotImplementedError(
                        'Unexpected token prefix "%s"' % i_leaf.prefix)

                leaf_len = len(str(i_leaf))
                cumulative_len += leaf_len

                if cumulative_len >= max_width:
                    if ',' in i_leaf.prefix:
                        i_leaf.prefix = ','
                    else:
                        i_leaf.prefix = ''
                    indentation = ' ' * (4 + indent)
                    i_leaf.prefix += '\n' + indentation
                    leaf_len = len(indentation) + len(str(i_leaf.value))
                    cumulative_len = leaf_len
