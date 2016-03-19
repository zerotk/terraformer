"""
Patches and fixes for lib2to3
"""
from __future__ import absolute_import, unicode_literals

import sys

from pypugly.text import dedent

from .memoize import Memoize

#=========================================================================
# Replace lib2to3.pgen2.driver.load_gramar to avoid depending on external file
# (Grammar.txt)
#=========================================================================

# This is the same as Grammar.txt, reproduced here to avoid dependency to
# external file.
GRAMMAR = {}
GRAMMAR['Grammar.txt'] = dedent(
    """
        # Grammar for 2to3. This grammar supports Python 2.x and 3.x.

        # Note:  Changing the grammar specified in this file will most likely
        #        require corresponding changes in the parser module
        #        (../Modules/parsermodule.c).  If you can't make the changes to
        #        that module yourself, please co-ordinate the required changes
        #        with someone who can; ask around on python-dev for help.  Fred
        #        Drake <fdrake@acm.org> will probably be listening there.

        # NOTE WELL: You should also follow all the steps listed in PEP 306,
        # "How to Change Python's Grammar"

        # Commands for Kees Blom's railroad program
        #diagram:token NAME
        #diagram:token NUMBER
        #diagram:token STRING
        #diagram:token NEWLINE
        #diagram:token ENDMARKER
        #diagram:token INDENT
        #diagram:output\input python.bla
        #diagram:token DEDENT
        #diagram:output\textwidth 20.04cm\oddsidemargin  0.0cm\evensidemargin 0.0cm
        #diagram:rules

        # Start symbols for the grammar:
        #    file_input is a module or sequence of commands read from an input file;
        #    single_input is a single interactive statement;
        #    eval_input is the input for the eval() and input() functions.
        # NB: compound_stmt in single_input is followed by extra NEWLINE!
        file_input: (NEWLINE | stmt)* ENDMARKER
        single_input: NEWLINE | simple_stmt | compound_stmt NEWLINE
        eval_input: testlist NEWLINE* ENDMARKER

        decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        decorators: decorator+
        decorated: decorators (classdef | funcdef)
        funcdef: 'def' NAME parameters ['->' test] ':' suite
        parameters: '(' [typedargslist] ')'
        typedargslist: ((tfpdef ['=' test] ',')*
                        ('*' [tname] (',' tname ['=' test])* [',' '**' tname] | '**' tname)
                        | tfpdef ['=' test] (',' tfpdef ['=' test])* [','])
        tname: NAME [':' test]
        tfpdef: tname | '(' tfplist ')'
        tfplist: tfpdef (',' tfpdef)* [',']
        varargslist: ((vfpdef ['=' test] ',')*
                      ('*' [vname] (',' vname ['=' test])*  [',' '**' vname] | '**' vname)
                      | vfpdef ['=' test] (',' vfpdef ['=' test])* [','])
        vname: NAME
        vfpdef: vname | '(' vfplist ')'
        vfplist: vfpdef (',' vfpdef)* [',']

        stmt: simple_stmt | compound_stmt
        simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE
        small_stmt: (expr_stmt | print_stmt  | del_stmt | pass_stmt | flow_stmt |
                     import_stmt | global_stmt | exec_stmt | assert_stmt)
        expr_stmt: testlist_star_expr (augassign (yield_expr|testlist) |
                             ('=' (yield_expr|testlist_star_expr))*)
        testlist_star_expr: (test|star_expr) (',' (test|star_expr))* [',']
        augassign: ('+=' | '-=' | '*=' | '@=' | '/=' | '%=' | '&=' | '|=' | '^=' |
                    '<<=' | '>>=' | '**=' | '//=')
        # For normal assignments, additional restrictions enforced by the interpreter
        print_stmt: 'print' ( [ test (',' test)* [','] ] |
                              '>>' test [ (',' test)+ [','] ] )
        del_stmt: 'del' exprlist
        pass_stmt: 'pass'
        flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt | yield_stmt
        break_stmt: 'break'
        continue_stmt: 'continue'
        return_stmt: 'return' [testlist]
        yield_stmt: yield_expr
        raise_stmt: 'raise' [test ['from' test | ',' test [',' test]]]
        import_stmt: import_name | import_from
        import_name: 'import' dotted_as_names
        import_from: ('from' ('.'* dotted_name | '.'+)
                      'import' ('*' | '(' import_as_names ')' | import_as_names))
        import_as_name: NAME ['as' NAME]
        dotted_as_name: dotted_name ['as' NAME]
        import_as_names: import_as_name (',' import_as_name)* [',']
        dotted_as_names: dotted_as_name (',' dotted_as_name)*
        dotted_name: NAME ('.' NAME)*
        global_stmt: ('global' | 'nonlocal') NAME (',' NAME)*
        exec_stmt: 'exec' expr ['in' test [',' test]]
        assert_stmt: 'assert' test [',' test]

        compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | with_stmt | funcdef | classdef | decorated
        if_stmt: 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        while_stmt: 'while' test ':' suite ['else' ':' suite]
        for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]
        try_stmt: ('try' ':' suite
                   ((except_clause ':' suite)+
                ['else' ':' suite]
                ['finally' ':' suite] |
               'finally' ':' suite))
        with_stmt: 'with' with_item (',' with_item)*  ':' suite
        with_item: test ['as' expr]
        with_var: 'as' expr
        # NB compile.c makes sure that the default except clause is last
        except_clause: 'except' [test [(',' | 'as') test]]
        suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT

        # Backward compatibility cruft to support:
        # [ x for x in lambda: True, lambda: False if x() ]
        # even while also allowing:
        # lambda x: 5 if x else 2
        # (But not a mix of the two)
        testlist_safe: old_test [(',' old_test)+ [',']]
        old_test: or_test | old_lambdef
        old_lambdef: 'lambda' [varargslist] ':' old_test

        test: or_test ['if' or_test 'else' test] | lambdef
        or_test: and_test ('or' and_test)*
        and_test: not_test ('and' not_test)*
        not_test: 'not' not_test | comparison
        comparison: expr (comp_op expr)*
        comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not'
        star_expr: '*' expr
        expr: xor_expr ('|' xor_expr)*
        xor_expr: and_expr ('^' and_expr)*
        and_expr: shift_expr ('&' shift_expr)*
        shift_expr: arith_expr (('<<'|'>>') arith_expr)*
        arith_expr: term (('+'|'-') term)*
        term: factor (('*'|'@'|'/'|'%'|'//') factor)*
        factor: ('+'|'-'|'~') factor | power
        power: atom trailer* ['**' factor]
        atom: ('(' [yield_expr|testlist_gexp] ')' |
               '[' [listmaker] ']' |
               '{' [dictsetmaker] '}' |
               '`' testlist1 '`' |
               NAME | NUMBER | STRING+ | '.' '.' '.')
        listmaker: (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
        testlist_gexp: (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
        lambdef: 'lambda' [varargslist] ':' test
        trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
        subscriptlist: subscript (',' subscript)* [',']
        subscript: test | [test] ':' [test] [sliceop]
        sliceop: ':' [test]
        exprlist: (expr|star_expr) (',' (expr|star_expr))* [',']
        testlist: test (',' test)* [',']
        dictsetmaker: ( (test ':' test (comp_for | (',' test ':' test)* [','])) |
                        (test (comp_for | (',' test)* [','])) )

        classdef: 'class' NAME ['(' [arglist] ')'] ':' suite

        arglist: (argument ',')* (argument [',']
                                 |'*' test (',' argument)* [',' '**' test]
                                 |'**' test)
        argument: test [comp_for] | test '=' test  # Really [keyword '='] test

        comp_iter: comp_for | comp_if
        comp_for: 'for' exprlist 'in' testlist_safe [comp_iter]
        comp_if: 'if' old_test [comp_iter]

        testlist1: test (',' test)*

        # not used in grammar, but may appear in "node" passed from Parser to Compiler
        encoding_decl: NAME

        yield_expr: 'yield' [yield_arg]
        yield_arg: 'from' test | testlist

        """
)
GRAMMAR['PatternGrammar.txt'] = dedent(
    """
        # Copyright 2006 Google, Inc. All Rights Reserved.
        # Licensed to PSF under a Contributor Agreement.

        # A grammar to describe tree matching patterns.
        # Not shown here:
        # - 'TOKEN' stands for any token (leaf node)
        # - 'any' stands for any node (leaf or interior)
        # With 'any' we can still specify the sub-structure.

        # The start symbol is 'Matcher'.

        Matcher: Alternatives ENDMARKER

        Alternatives: Alternative ('|' Alternative)*

        Alternative: (Unit | NegatedUnit)+

        Unit: [NAME '='] ( STRING [Repeater]
                         | NAME [Details] [Repeater]
                         | '(' Alternatives ')' [Repeater]
                         | '[' Alternatives ']'
                 )

        NegatedUnit: 'not' (STRING | NAME [Details] | '(' Alternatives ')')

        Repeater: '*' | '+' | '{' NUMBER [',' NUMBER] '}'

        Details: '<' Alternatives '>'

    """
)


@Memoize
def LoadGrammar(gt="Grammar.txt", gp=None, save=True, force=False, logger=None):
    """
    We replace the function that generates the grammar to remove the dependency with external
    files.

    This is necessary because we want to be able to use lib2to3 inside an executable.

    :param filename:
        The gramar filename.

    :return PgenGrammar:
    """
    from cStringIO import StringIO
    import lib2to3.pgen2.pgen
    import os

    p = lib2to3.pgen2.pgen.ParserGenerator(
        gt,
        stream=StringIO(bytes(GRAMMAR[os.path.basename(gt)]))
    )
    return p.make_grammar()


if sys.version_info[:3] == (2, 7, 7):
    # Only replace the LoadGrammar on Python 2.7.7, which matches with our stored grammar.
    # On other version (CentOS 7) uses the system algorithm. Remember that without this algorithm
    # we can't create executables that uses lib2to3.
    import lib2to3.pgen2.driver
    lib2to3.pgen2.driver.load_grammar = LoadGrammar


#=========================================================================
# GetNodeLineNumber
#=========================================================================
def GetNodeLineNumber(node):
    """
    Returns the given node line number.

    :param lib2to3.Node node:

    :return int:
    """
    parent = node
    while parent:
        if hasattr(parent, 'lineno'):
            return parent.lineno
        parent = parent.parent
    return 0


#=========================================================================
# GetNodePosition
#=========================================================================
def GetNodePosition(node):
    """
    Returns the given node position (line number and column).

    NOTE: Not quite sure which is the best way of obtaining the line number, this one or
    GetNodeLineNumber.

    :param lib2to3.Node node:

    :return tuple(int, int):
    """
    try:
        child = node[0]
    except:
        child = node
    while child:
        if hasattr(child, 'lineno'):
            lineno = child.lineno - child.prefix.count('\n')
            return (lineno, child.column)
        child = child.children[0]
    return (0, 0)
