from __future__ import unicode_literals



#===================================================================================================
# ASTError
#===================================================================================================
class ASTError(Exception):
    '''
    Exception associated with any error handling the AST tree.

    This is actually a visitor error sinde the AST tree must be well formed before we start.
    '''



#===================================================================================================
# ASTVisitor
#===================================================================================================
class ASTVisitor(object):
    '''
    The ASTVisitor walk through the code ast nodes calling specific methods for specific matches on
    the code.

    The methods called directly by the AST-Visitor are prefixed by "_Visit". The class attribute
    PATTERNS maps AST regexes with the respective visit method.

    The methods prefixed with "Visit" are called with better (processed) parameters than "_Visit"
    methods.
    '''

    PATTERNS = [
        ('_VisitAll', "file_input< nodes=any* >"),
        ('_VisitAll', "suite< nodes=any* >"),
        ('_VisitClass', "body=classdef< 'class' name=NAME ['(' bases=any ')'] ':' any >"),
        ('_VisitFunction', "body=funcdef< 'def' name=NAME parameters< '(' [args=any] ')' > ':' any >"),
        ('_VisitImport',
            "body=import_name< 'import' names=any > | "
            "body=import_from< 'from' import_from=any 'import' names=any > | "
            "body=import_from< 'from' import_from=any 'import' '(' names=any ')' >"
        ),
        ('_VisitPowerSymbol', "body=power< left=NAME trailer< middle='.' right=NAME > any* >"),
        ('_VisitAssignment', "body=expr_stmt< name=any '=' value=any >"),
    ]

    def __init__(self):
        self.patterns = []
        self._assignment = 0
        for method, pattern in self.PATTERNS:
            self._RegisterPattern(method, pattern)

        self._module = None
        self._current_import_block = None
        self._scope_stack = []
        self._klass_stack = []
        self.import_blocks = []
        self.symbols = set()
        self.__assignment = False


    def _RegisterPattern(self, method, pattern):
        '''
        Registers a new pattern and the handling method.

        :param str method:
            The method name to handle the node matching the pattern.

        :param str pattern:
            The pattern to match AST nodes.
            This follows the lib2to3 pattern syntax.
        '''
        from lib2to3.patcomp import compile_pattern
        self.patterns.append((method, compile_pattern(pattern)))


    def Visit(self, tree):
        '''
        Main entry point of the ASTVisitor class.

        Visits AST nodes calling specific _VisitXXX implementation based on matching patterns.

        :param lib2to3.Node tree:
            A lib2to3 AST tree.
        '''
        self.EvVisitStart(tree)
        self._Visit(tree)
        self.EvVisitEnd(tree)


    # Events ---------------------------------------------------------------------------------------

    def EvVisitStart(self, tree):
        '''
        Event associated with the start of the AST visiting.

        :param lib2to3.Node tree:
        '''
        from ._symbol import ModuleScope
        from lib2to3.pygram import python_symbols
        from lib2to3.pytree import Leaf

        # Find the code-position for the import-block. Either a leaf or an import statement.
        types=(python_symbols.import_from, python_symbols.import_name)
        code_position = tree
        while not isinstance(code_position, Leaf) and code_position.type not in types:
            code_position = code_position.children[0]

        # Module scope.
        self._module = ModuleScope(None, 'module', tree)
        self._scope_stack.append(self._module)


    def _CreateImportBlock(self, parent, code_position, code_replace, lineno, indent=0):
        '''
        Creates a import-block, a semantic scope that groups import-statements.

        :param Symbol parent:
            The parent symbol for the import-block

        :param lib2to3.Node code_position:
            Mark the position where the code is placed.
            This is used to identify where to add/replace code.

        :param list(lib2to3.Node) code_replace:
            Mark the code that must be replaced by the import-block.

        :param lineno:
            The reference line-number (used for debug purposes)

        :param indent:
            The import-block indentation level (in number of characters).

        :return ImportBlockScope:
        '''
        from ._symbol import ImportBlock

        id = len(self.import_blocks)
        self._current_import_block = ImportBlock(
            parent,
            code_position,
            code_replace,
            id,
            lineno,
            indent
        )
        self.import_blocks.append(self._current_import_block)
        return self._current_import_block


    def EvVisitEnd(self, tree):
        '''
        Event associated with the end of the AST visiting.

        :param lib2to3.Node tree:
        '''


    def EvVisitLeaf(self, leaf):
        '''
        Visiting a leaf node.

        In this implementation we handle two things:
        * Connecting import-statements togeter into import-blocks.
        * Identifying name tokens (either definition or use).

        :param lib2to3.Leaf leaf:
        '''
        from lib2to3.pgen2 import token

        def CreateImportBlockZero(code_position):
            if code_position.type == token.STRING:
                return

            if code_position.type == token.NEWLINE and not code_position.prefix:
                return

            lineno = self._GetImportBlockLineNumber(code_position)
            self._CreateImportBlock(self._module, code_position, code_replace=[], lineno=lineno)

        # Create import-block zero, a place-holder for import-symbols additions.
        if not self.import_blocks:
            CreateImportBlockZero(leaf)

        # Handle import-block, connecting import-symbols.
        if self._current_import_block:
            # Append 'intermediate' tokens to the import-block or reset it.
            if leaf.value in (u'\n', u'\r\n'):
                self._current_import_block.code_replace.append(leaf)
            else:
                self._current_import_block = None

        # Handle NAME tokens.
        # NOTE: Can't use DEFAULT_PATTERNS because those are only for Nodes.
        if leaf.type in (token.NAME,):
            self.EvVisitName(leaf)


    def EvVisitName(self, body):
        '''
        Visiting a name.

        NOTE: Today we have two ways of identifying symbols definitions and usage: EvVisitSymbol and
        EvVisitName

        :param lib2to3.Leaf body:
        '''
        current_scope = self._scope_stack[-1]
        symbol = body.value

        if self._assignment == 1:  # Assignee
            current_scope.AddSymbolDefinition(symbol, body)
        if self._assignment == 2:  # Value
            current_scope.AddSymbolUsage(symbol, body)


    def EvVisitImport(self, names, import_from, body):
        '''
        Visiting an import statement.

        :param list(str) names:
            The names being imported.

        :param str import_from:
            The package name if importing using "import-from" syntax.

        :param lib2to3.Node body:
            The raw AST node with the import-statement.
        '''
        from ._lib2to3 import GetNodeLineNumber

        if not self.import_blocks and body.prefix:
            # Create Import-block-zero before the first import-statement IF we have a prefix, that
            # is, a comment block or line-ends.
            lineno = self._GetImportBlockLineNumber(body)
            self._CreateImportBlock(self._module, body, code_replace=[], lineno=lineno)

        # Obtain the import-block for these statements, creating if necessary.
        first_leaf = self._GetFirstLeaf(body)
        prefix = first_leaf.prefix
        has_line_comment = '#' in prefix
        indent = first_leaf.column
        if self._current_import_block and not has_line_comment and self._current_import_block.column == indent:
            code_replace = [body]
            connection_node = body.next_sibling
            while connection_node and connection_node.value in (u'\n'):
                code_replace.append(connection_node)
                connection_node = connection_node.next_sibling
            self._current_import_block.code_replace += code_replace
        else:
            self._CreateNewImportBlock(body, prefix, indent)

        # Create import-symbols.
        lineno = GetNodeLineNumber(first_leaf)
        next_node = body.next_sibling
        inline_comment = next_node.prefix
        symbols = self._CreateImportSymbols(names, import_from, inline_comment, lineno)

        self.symbols.update(set(symbols))


    def _CreateImportSymbols(self, names, import_from, inline_comment, lineno):
        '''
        Creates import-symbols.
        '''
        from ._symbol import ImportSymbol, ImportBlock

        assert self._current_import_block is not None
        assert isinstance(self._current_import_block, ImportBlock)

        result = set()
        for i_name in names:
            if isinstance(i_name, tuple):
                i_name, import_as = i_name
            else:
                import_as = None

            if import_from:
                symbol = '%s.%s' % (import_from, i_name)
                kind = ImportSymbol.KIND_IMPORT_FROM
            else:
                symbol = i_name
                kind = ImportSymbol.KIND_IMPORT_NAME

            r = self._current_import_block.ObtainImportSymbol(
                symbol,
                import_as,
                inline_comment,
                kind,
                lineno
            )
            result.add(r)
        return result


    def EvVisitSymbol(self, symbol, nodes, body):
        '''
        Visiting a (power) symbol, that is, a symbol defined as an
        attribute of another symbol (Eg.: alpha.bravo).

        NOTE: Today we have two ways of identifying symbols definitions and usage: EvVisitSymbol and
        EvVisitName
        '''
        current_scope = self._scope_stack[-1]
        if self._assignment == 1:  # Assignee
            current_scope.AddSymbolDefinition(symbol, body)
        else:
            current_scope.AddSymbolUsage(symbol, body, code_replace=nodes)


    def EvVisitAssignment(self, name, value, body):
        '''
        Visiting an assignment statement.

        We use the _assignment attribute and continue visiting both sides of the assignment.
        Elsewhere we check the _assignment attribute to know if the name/symbol is being defined or
        used.

        :param lib2to3.Node name:
            The left node for the assignment.

        :param lib2to3.Node value:
            The right node for the assignment.

        :param body:
            The entire assignment body.
        '''
        assert len(body.children) == 3
        assert body.children[0] is name
        assert body.children[2] is value
        self._current_import_block = None
        self._assignment = 1
        self._Visit(name)
        self._assignment = 2
        self._Visit(value)
        self.__assignment = 0


    def EvVisitClass(self, name, bases, body):
        '''
        Visiting a class definition.

        :param str name: The name of the class.
        :param list(str) bases: The base classes.
        :param lib2to3.Node body: The (entire) class definition body Node.
        '''
        from ._symbol import ClassScope, FunctionScope

        self._current_import_block = None

        parent = self._scope_stack[-1]

        # Add this class bases uses
        for i_base in bases:
            parent.AddSymbolUsage(i_base, body)

        # NOTE: nodes should point to the class name node (for renaming), not the entire code.
        scope = ClassScope(parent, name, None)
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1

        self._klass_stack.append(scope)
        self._scope_stack.append(scope)
        self._Visit(body.children)  # Visit only CODE child, not the class declaration.
        self._scope_stack.pop()
        self._klass_stack.pop()


    def EvVisitFuncion(self, name, args, body):
        '''
        Visiting function definition.

        :param str name: The name of the function.
        :param list(str) args: The function arguments
        :param lib2to3.Node body: The (entire) function definition body Node.
        '''
        from ._symbol import FunctionScope

        self._current_import_block = None

        parent = self._scope_stack[-1]
        scope = FunctionScope(parent, name, body)  # NOTE: We should have the function name as body.
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1

        scope.HandleArgs(args, body)

        self._scope_stack.append(scope)
        self._Visit(body.children)
        self._scope_stack.pop()


    # Utitilites -----------------------------------------------------------------------------------

    def _GetImportBlockLineNumber(self, node):
        '''
        Obtain the line number for the import-block.

        NOTE: WIP: return a valid number but not the correct line number.
        '''
        from ._lib2to3 import GetNodeLineNumber

        return GetNodeLineNumber(node) - node.prefix.count('\n')


    def _GetFirstLeaf(self, node):
        '''
        Returns the first leaf child from the given node.

        :param lib2to3.Node node:

        :return lib2to3.Leaf:
        '''
        from lib2to3.pytree import Leaf

        r_leaf = node
        while not isinstance(r_leaf, Leaf):
            r_leaf = r_leaf.children[0]
        return r_leaf


    def _CreateNewImportBlock(self, body, prefix, indent):
        '''
        Create a new import-block.
        '''
        from ._lib2to3 import GetNodeLineNumber

        code_replace = [body]
        connection_node = body.next_sibling
        while connection_node and connection_node.value in (u'\n', u'\r\n'):
            code_replace.append(connection_node)
            connection_node = connection_node.next_sibling

        parent = self._scope_stack[-1]
        return self._CreateImportBlock(
            parent,
            code_position=body,
            code_replace=code_replace,
            lineno=GetNodeLineNumber(body),
            indent=indent
        )


    # Pattern Handlers -----------------------------------------------------------------------------

    def _Visit(self, tree):
        '''
        Recursive implementation of Visit.

        :param lib2to3.Node tree:
            A lib2to3 AST tree.
        '''
        from lib2to3.pytree import Leaf, Node

        if isinstance(tree, Leaf):
            self.EvVisitLeaf(tree)
        elif isinstance(tree, Node):
            self._VisitNode(tree)
        elif isinstance(tree, list):
            for subtree in tree:
                self._Visit(subtree)
        else:
            raise ASTError("Unknown tree type: %r." % tree)


    def _VisitAll(self, results):
        '''
        Top level visitor handler.
        '''
        self._Visit(results['nodes'])


    def _VisitNode(self, node):
        '''
        Visitor handler for nodes.
        Check for matching pattern (and matching visitor handler) or visits each child node.
        '''
        for method, pattern in self.patterns:
            results = {}
            if pattern.match(node, results):
                getattr(self, method)(results)
                break
        else:
            # For unknown nodes simply descend to their list of children.
            self._Visit(node.children)


    def _VisitClass(self, results):
        '''
        Visitor handler for class.
        Organize the parameters to call EvVisitClass.
        '''
        self.EvVisitClass(
            name=results['name'].value,
            bases=_DeriveClassNames(results.get('bases')),
            body=results['body']
        )


    def _VisitFunction(self, results):
        '''
        Visitor handler for function/method.
        Organize the parameters to call EvVisitFunction.
        '''
        self.EvVisitFuncion(
            name=results['name'].value,
            args=_DeriveArguments(results.get('args', [])),
            body=results['body']
        )


    def _VisitImport(self, results):
        '''
        Visitor handler for import-statement.
        Organize the parameters to call EvVisitImport.
        '''
        self.EvVisitImport(
            names=_DeriveImportNames(results['names']),
            import_from=_DeriveImportName(results.get('import_from')),
            body=results['body']
        )


    def _VisitPowerSymbol(self, results):
        '''
        Visitor handler for power symbols.
        Organize the parameters to call EvVisitSymbol.
        '''
        left=results.get('left')
        middle=results.get('middle')
        right=results.get('right')
        body=results['body']
        self.EvVisitSymbol(
            symbol=u'.'.join((left.value, right.value)),
            nodes=[left,middle,right],
            body=body
        )
        self._Visit(body.children[2:])


    def _VisitAssignment(self, results):
        '''
        Visitor handler for assignments.
        Organize the parameters to call EvVisitAssignment.
        '''
        name=results.get('name')
        value=results.get('value')
        self.EvVisitAssignment(
            name=name,
            value=value,
            body=results['body']
        )



#===================================================================================================
# Utility Functions
# This code is inspired on pythonscope astvisitor.py:
#   https://github.com/mkwiatkowski/pythoscope/blob/890af15a88c2fbf2197b40f5de53493b48b61d8e/pythoscope/astvisitor.py
#===================================================================================================


def _IsLeafOfType(leaf, *types):
    '''
    Check if the leaf is of one of the given types.

    :param lib2to3.Leaf leaf:

    :param int types:
        Usually a token.XXX constant.

    :return bool:
    '''
    from lib2to3.pytree import Leaf

    return isinstance(leaf, Leaf) and leaf.type in types


def _IsNodeOfType(node, *types):
    '''
    Check if the node is of one of the given types.

    :param lib2to3.Node node:

    :param unicode types:
        The name of the node type.

    :return bool:
    '''
    from lib2to3.pytree import Node, type_repr
    return isinstance(node, Node) and type_repr(node.type) in types


def _RemoveCommas(nodes):
    '''
    Remove comma nodes from the given list of nodes.

    Used to remove commas from the function/method argument list.

    :param list(lib2to3.Node) nodes:
    :return list(list2to3.Node):
    '''
    from lib2to3.pgen2 import token

    return [i for i in nodes if not _IsLeafOfType(i, token.COMMA)]


def _RemoveDefaults(nodes):
    '''
    Remove default values from a list of nodes.

    Used to remove the default values from the function/method argument list.

    :param list(lib2to3.Node) nodes:
    :return iter(list2to3.Node):
    '''
    from lib2to3.pgen2 import token

    ignore_next = False
    for node in nodes:
        if ignore_next is True:
            ignore_next = False
            continue
        if _IsLeafOfType(node, token.EQUAL):
            ignore_next = True
            continue
        yield node


def _DeriveClassName(node):
    '''
    Clean-up a node that represents a class name.

    :param lib2to3.Node node:
    :return unicode:
    '''
    return unicode(node).strip()


def _DeriveClassNames(node):
    '''
    Clean-up a node that represents a list of classes (derived classes).

    :param lib2to3.Node node:
    :return list(unicode):
    '''
    if node is None:
        return []
    elif _IsNodeOfType(node, 'arglist'):
        return map(_DeriveClassName, _RemoveCommas(node.children))
    else:
        return [_DeriveClassName(node)]


def _DeriveArgument(node):
    '''
    Returns a node or tuple of nodes for the node.

    :param lib2to3.Node node:
    :return lib2to3.Node|tuple(lib2to3.Node):
    '''
    from lib2to3.pgen2 import token

    if _IsLeafOfType(node, token.NAME):
        return node
    elif _IsNodeOfType(node, 'tfpdef'):
        return tuple(
            map(
                _DeriveArgument,
                _RemoveCommas(node.children[1].children)
            )
        )


def _DeriveArgumentsFromTypedArgList(node):
    '''
    Returns a list of arguments from a node of type "typedarglist".

    NOTE: I converted this method to return the Node instead of the string. With this I've lost the
    start and double-star prefix that was added to the resulting string.

    :param lib2to3.Node node:
    :return list(lib2to3.Node):
    '''
    from lib2to3.pgen2 import token

    prefix = ''
    for i_node in _RemoveDefaults(_RemoveCommas(node.children)):
        if _IsLeafOfType(i_node, token.STAR):
            prefix = '*'
        elif _IsLeafOfType(i_node, token.DOUBLESTAR):
            prefix = '**'
        elif prefix:
            yield _DeriveArgument(i_node)
            prefix = ''
        else:
            yield _DeriveArgument(i_node)


def _DeriveArguments(node):
    '''
    Returns a list of arguments from a node.

    NOTE: I converted this method to return the Node instead of the string.

    :param lib2to3.Node node:
    :return list(lib2to3.Node):
    '''
    if node == []:
        return []
    elif _IsNodeOfType(node, 'typedargslist'):
        return list(_DeriveArgumentsFromTypedArgList(node))
    else:
        return [_DeriveArgument(node)]


def _DeriveImportName(node):
    '''
    Returns the text for the given "import name" node.

    :param lib2to3.Node node:
    :return unicode:
    '''
    from lib2to3.pgen2 import token

    if _IsLeafOfType(node, token.NAME, token.STAR, token.DOT):
        return node.value
    elif _IsNodeOfType(node, 'dotted_as_name', 'import_as_name'):
        return (
            _DeriveImportName(node.children[0]),
            _DeriveImportName(node.children[2])
        )
    elif _IsNodeOfType(node, 'dotted_name'):
        return "".join([i.value for i in node.children])
    elif node is None:
        return
    else:
        raise ASTError("_DeriveImportName: unknown node type: %r." % node)


def _DeriveImportNames(node):
    '''
    Returns the text for the given "import names" node.

    :param lib2to3.Node node:
    :return list(unicode):
    '''
    if node is None:
        return None
    elif _IsNodeOfType(node, 'dotted_as_names', 'import_as_names'):
        return map(
            _DeriveImportName,
            _RemoveCommas(node.children)
        )
    else:
        return [_DeriveImportName(node)]
