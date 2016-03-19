from __future__ import unicode_literals

from zerotk.easyfs import GetFileContents

from .memoize import Memoize
from .module_finder import ModuleFinder


class FileTooBigError(RuntimeError):
    """
    Exception raised when a big file is detected.
    We raise this exception before asking lib2to3 to handle it because if we let this to lib2to3 we
    end getting a infinite loop.
    """

    def __init__(self, filename, size):
        RuntimeError.__init__(self, 'File %s too big: %d' % (filename, size))


class TerraFormer(object):
    """
    Python code refactoring class.

    # Reorganize Imports:

    ### Unsupported cases:
    * Import with dots:
        import .alpha
        ---
        import .alpha

    """

    MAX_FILE_SIZE = 500000

    def __init__(self, source=None, filename=None):
        if source is None:
            # Stores the original loaded sources into __source.
            # This variable must be updated if we happen to save the file with
            # any changes.
            self.__original_source = GetFileContents(
                filename, newline='', encoding='UTF-8')
        else:
            self.__original_source = source

        file_size = len(self.__original_source)
        if file_size > self.MAX_FILE_SIZE:
            # Some big files make the Parse algorithm get stuck.
            raise FileTooBigError(filename, file_size)

        self.filename = filename
        self.symbols = set()
        self.names = set()
        self.import_blocks = []

        self.code = self._Parse(self.__original_source)

        from ._visitor import ASTVisitor
        visitor = ASTVisitor()
        visitor.Visit(self.code)
        self.module, self.symbols, self.import_blocks = visitor._module, visitor.symbols, visitor.import_blocks

    def GenerateSource(self):
        """
        Generates the source code from the AST Tree.

        :return unicode:
        """
        return unicode(self.code)

    @classmethod
    @Memoize(maxsize=1000)
    def Factory(cls, filename, source=None):
        """
        Creates a TerraFormer instance using a cache to speed up.

        :param str filename: Python module filename.

        :param str source: Optinal python module sources.

        :return TerraFormer:
        """
        return cls(source=source, filename=filename)

    @classmethod
    def _QuotedBlock(cls, text):
        """
        Auxiliary function to "quote" a multiline text.

        :param str text:

        :return str:
        """
        return ''.join(["> %s" % line for line in text.splitlines(True)])

    @classmethod
    def _Parse(cls, code):
        """
        Parses the given code string returning its lib2to3 AST tree.

        :return lib2to3.AST:
            Returns the lib2to3 AST.
        """

        def _GetLastLeaf(node):
            from lib2to3.pytree import Leaf

            r_leaf = node
            while not isinstance(r_leaf, Leaf):
                r_leaf = r_leaf.children[-1]
            return r_leaf

        # Prioritary import.
        from . import _lib2to3  # @NotUsedImport

        # Other imports
        from zerotk.reraiseit import reraise
        from lib2to3 import pygram, pytree
        from lib2to3.pgen2 import driver
        from lib2to3.pgen2.parse import ParseError
        from lib2to3.pygram import python_symbols
        from lib2to3.pytree import Leaf, Node
        from lib2to3.refactor import _detect_future_features

        added_newline = code and not code.endswith('\n')
        if added_newline:
            code += '\n'

        # Selects the appropriate grammar depending on the usage of
        # "print_function" future feature.
        future_features = _detect_future_features(code)
        if 'print_function' in future_features:
            grammar = pygram.python_grammar_no_print_statement
        else:
            grammar = pygram.python_grammar

        try:
            drv = driver.Driver(grammar, pytree.convert)
            result = drv.parse_string(code, True)
        except ParseError as e:
            reraise(e, "Had problems parsing:\n%s\n" % cls._QuotedBlock(code))

        # Always return a Node, not a Leaf.
        if isinstance(result, Leaf):
            result = Node(python_symbols.file_input, [result])

        # Remove AST-leaf for the added newline.
        if added_newline:
            last_leaf = _GetLastLeaf(result)
            if not (last_leaf.type == 0 and last_leaf.value == ''):
                if last_leaf.prefix:
                    last_leaf.prefix = last_leaf.prefix[:-1]
                else:
                    last_leaf.remove()

        return result

    @classmethod
    def WalkLeafs(cls, node):
        """
        Walks leafs on the given node.

        :param node lib2to3.pytree.Node:
        :return lib2to3.pytree.Leaf:
        """
        from lib2to3.pytree import Leaf

        if isinstance(node, Leaf):
            yield node
        else:
            for i_child in node.children:
                for j_leaf in cls.WalkLeafs(i_child):
                    yield j_leaf

    def GetSymbolFromToken(self, token):
        """
        Returns the symbol instance for the given token.

        :param unicode token:
        :return Symbol:
        """
        tokens = {i.GetToken(): i for i in self.symbols}
        return tokens.get(token)

    def GetModuleName(self):
        """
        Returns the python module name.
        Ex.
            alpha10.parent.working.py -> alpha10.parent

        IMPORTANT: For this to work the package must be importable in the current PYTHONPATH.

        :return str:
            The module name in the format:
                xxx.yyy.zzz
        """
        module_finder = ModuleFinder()
        try:
            return module_finder.ModuleName(self.filename).rsplit('.', 1)[0]
        except RuntimeError:
            return None

    def ReorganizeImports(
        self,
        refactor={},
        page_width=100
    ):
        """
        Reorganizes all imports-blocks.

        :param dict refactor:
            A dictionary mapping old symbols to new symbols.

        :param int page_width:
            The page-width to format the import statements.

        :return boolean:
            Returns True if any changes were made.
        """
        for i_import_block in self.import_blocks:
            i_import_block.Reorganize(page_width, refactor, self.filename)
        return self.__original_source != self.GenerateSource()

    def Save(self):
        """
        Saves the filename applying the changes made by previous method calls.
        """
        from zerotk.easyfs import CreateFile, EOL_STYLE_UNIX

        assert self.filename is not None, "No filename set on TerraFormer."
        assert self.__original_source is not None, "No original content set on TerraFormer."

        new_source = self.GenerateSource()
        changed = new_source != self.__original_source

        if changed:
            self.__original_source = self.GenerateSource()
            CreateFile(
                self.filename,
                self.__original_source,
                eol_style=EOL_STYLE_UNIX,
                encoding='UTF-8'
            )

        return changed

    def AddImportSymbol(self, import_symbol):
        """
        Adds a import-symbol in the top of the python module.

        :param str import_symbol:
            The import-symbol to add.
            Eg.: __futures__.with_statement
        """
        from ._symbol import ImportSymbol

        import_block = self.import_blocks[0]
        symbol = import_block.ObtainImportSymbol(
            import_symbol, kind=ImportSymbol.KIND_IMPORT_FROM)
        if symbol:
            self.symbols.add(symbol)
