from __future__ import unicode_literals

from zerotk.clikit.pushpop import PushPop
from zerotk.terraformer import TerraFormer
from pypugly.text import dedent
import pytest



def testImportBlockZero(monkeypatch, embed_data):

    def TestIt(input, symbols, expected, import_blocks):
        input = dedent(input)
        expected = dedent(expected) + '\n'

        terra_former = TerraFormer(input)
        for i_symbol in symbols:
            terra_former.AddImportSymbol(i_symbol)
        terra_former.ReorganizeImports()

        # Make sure that creating a TerraFormer won't make any changes to the AST
        assert terra_former.GenerateSource() == expected

        assert map(str, terra_former.import_blocks) == import_blocks

    TestIt(
        '''

        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
        ]
    )

    TestIt(
        '''

        ''',
        ['io'],
        '''
        import io
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT (0, 0) io',
        ]
    )

    TestIt(
        '''
        from __future__ import unicode_literals
        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (1, 0) __future__.unicode_literals',
        ]
    )

    TestIt(
        '''
        def Function():
            pass
        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        def Function():
            pass
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
        ]
    )

    TestIt(
        '''
        """
        Docs
        """

        def Function():
            pass
        ''',
        ['__future__.unicode_literals'],
        '''
        """
        Docs
        """
        from __future__ import unicode_literals

        def Function():
            pass
        ''',
        [
            'IMPORT-BLOCK (4, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
        ]
    )

    TestIt(
        '''
        # Comments

        def Function():
            pass
        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        # Comments

        def Function():
            pass
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
        ]
    )

    TestIt(
        '''
        #===================================================================================================
        # PrintLine
        #===================================================================================================
        def PrintLine(s):
            """
            Docs
            """
            print s
        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        #===================================================================================================
        # PrintLine
        #===================================================================================================
        def PrintLine(s):
            """
            Docs
            """
            print s
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
        ]
    )

    TestIt(
        '''
        def Function(s):
            import alpha
        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        def Function(s):
            import alpha
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
            'IMPORT-BLOCK (2, 4) import-block #1\n  IMPORT (2, 0) alpha',
        ]
    )

    TestIt(
        '''
        # [[[cog
        # from coilib50.cpp.import_bindings import RepublishCppSymbols
        # cog.out(RepublishCppSymbols(
        #     'coilib50._coilib50_cpp_module',
        #     ['RedirectOutput'],
        # ))
        # ]]]
        from coilib50 import _coilib50_cpp_module
        RedirectOutput = _coilib50_cpp_module.RedirectOutput
        # [[[end]]] (checksum: e19f682169067c207e055a3a169feba7)
        ''',
        ['__future__.unicode_literals'],
        '''
        from __future__ import unicode_literals
        # [[[cog
        # from coilib50.cpp.import_bindings import RepublishCppSymbols
        # cog.out(RepublishCppSymbols(
        #     'coilib50._coilib50_cpp_module',
        #     ['RedirectOutput'],
        # ))
        # ]]]
        from coilib50 import _coilib50_cpp_module
        RedirectOutput = _coilib50_cpp_module.RedirectOutput
        # [[[end]]] (checksum: e19f682169067c207e055a3a169feba7)
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
            'IMPORT-BLOCK (1, 0) import-block #1\n  IMPORT-FROM (0, 0) coilib50\n    IMPORT (8, 0) coilib50._coilib50_cpp_module',
        ]
    )

    TestIt(
        '''


        import alpha
        ''',
        ['__future__.unicode_literals'],
        '''


        from __future__ import unicode_literals
        import alpha
        ''',
        [
            'IMPORT-BLOCK (1, 0) import-block #0\n  IMPORT (3, 0) alpha\n  IMPORT-FROM (0, 0) __future__\n    IMPORT (0, 0) __future__.unicode_literals',
        ]
    )


def testTerraFormer(monkeypatch, embed_data):

    terra_former = TerraFormer(
        source=dedent(
            '''
            import bravo
            import charlie
            from alpha import A1
            from bravo import (B1, B2, B3)
            # Delta Comment
            from delta.charlie.delta import DeltaClass

            from zulu import (Z1,
                Z2,  # Comment on Z2
                Z3
            )

            from yankee import Y1, \
                Y2, \
                Y3

            def Func():
                """
                Func is king.
                """
                import india_one
                var_alpha = alpha.AlphaClass()

                if True:
                    import india_in

                import india_out

            var_bravo = bravo.BravoClass()
            '''
        )
    )

    assert set([i.name for i in terra_former.symbols]) == {
        'alpha.A1',
        'bravo',
        'bravo.B1',
        'bravo.B2',
        'bravo.B3',
        'charlie',
        'delta.charlie.delta.DeltaClass',
        'india_one',
        'india_in',
        'india_out',
        'yankee.Y1',
        'yankee.Y2',
        'yankee.Y3',
        'zulu.Z1',
        'zulu.Z2',
        'zulu.Z3',
    }

    assert map(str, terra_former.import_blocks) == [
        'IMPORT-BLOCK (1, 0) import-block #0\n'
        '  IMPORT (1, 0) bravo\n'
        '  IMPORT (2, 0) charlie\n'
        '  IMPORT-FROM (0, 0) alpha\n'
        '    IMPORT (3, 0) alpha.A1\n'
        '  IMPORT-FROM (0, 0) bravo\n'
        '    IMPORT (4, 0) bravo.B1\n'
        '    IMPORT (4, 0) bravo.B2\n'
        '    IMPORT (4, 0) bravo.B3',
        'IMPORT-BLOCK (5, 0) import-block #1\n'
        '  IMPORT-FROM (0, 0) delta.charlie.delta\n'
        '    IMPORT (6, 0) delta.charlie.delta.DeltaClass\n'
        '  IMPORT-FROM (0, 0) zulu\n'
        '    IMPORT (8, 0) zulu.Z1\n'
        '    IMPORT (8, 0) zulu.Z2\n'
        '    IMPORT (8, 0) zulu.Z3\n'
        '  IMPORT-FROM (0, 0) yankee\n'
        '    IMPORT (13, 0) yankee.Y1\n'
        '    IMPORT (13, 0) yankee.Y2\n'
        '    IMPORT (13, 0) yankee.Y3',
        'IMPORT-BLOCK (19, 4) import-block #2\n'
        '  IMPORT (19, 0) india_one',
        'IMPORT-BLOCK (23, 8) import-block #3\n'
        '  IMPORT (23, 0) india_in',
        'IMPORT-BLOCK (25, 4) import-block #4\n'
        '  IMPORT (25, 0) india_out',
    ]

    changed = terra_former.ReorganizeImports()

    assert terra_former.GenerateSource() == dedent(
        '''
            from alpha import A1
            from bravo import B1, B2, B3
            import bravo
            import charlie
            # Delta Comment
            from delta.charlie.delta import DeltaClass
            from yankee import Y1, Y2, Y3
            from zulu import Z1, Z2, Z3

            def Func():
                """
                Func is king.
                """
                import india_one
                var_alpha = alpha.AlphaClass()

                if True:
                    import india_in

                import india_out

            var_bravo = bravo.BravoClass()

        '''
    )


def testReorganizeImports(embed_data, line_tester):
    from zerotk.easyfs import GetFileContents

    def Doit(lines):
        source = ''.join([i + '\n' for i in lines])
        terra = TerraFormer(source=source)
        changed_ = terra.ReorganizeImports(
            refactor={
                'coilib50.basic.implements': 'etk11.foundation.interface',
                'coilib50.basic.inter': 'etk11.foundation.interface',
                'coilib50.multithreading': 'multithreading',
                'before_refactor_alpha.Alpha': 'after_refactor.Alpha',
                'before_refactor_bravo.Bravo': 'after_refactor.Bravo',
            }
        )
        return terra.GenerateSource().splitlines()

    line_tester.TestLines(
        GetFileContents(embed_data['reorganize_imports.txt'], encoding='UTF-8'),
        Doit,
    )


def testQuotedBlock():
    assert TerraFormer._QuotedBlock(
        'alpha\nbravo\ncharlie\n'
    ) == '> alpha\n> bravo\n> charlie\n'


def testParse():
    from lib2to3.pgen2.parse import ParseError
    with pytest.raises(ParseError):
        TerraFormer._Parse('class Class:\n')


def testLocalImports(monkeypatch, embed_data):
    from zerotk.terraformer._symbol import ImportBlock

    monkeypatch.setattr(ImportBlock, 'PYTHON_EXT', '.py_')

    def TestIt(filename):
        full_filename = embed_data['testLocalImports/alpha/%s.py_' % filename]
        terra = TerraFormer(filename=full_filename)
        terra.ReorganizeImports()
        terra.Save()
        embed_data.assert_equal_files(
            embed_data['testLocalImports/alpha/%s.py_' % filename],
            embed_data['testLocalImports/alpha.expected/%s.py_' % filename]
        )

    import sys
    sys_path = [embed_data['testLocalImports']] + sys.path[:]
    with PushPop(sys, 'path', sys_path):
        TestIt('__init__')
        TestIt('_yankee')
        TestIt('_alpha_core')
        TestIt('simentar_test_base')
        TestIt('romeo')
        TestIt('quilo')

        # Test MAX_FILE_SIZE
        with pytest.raises(RuntimeError):
            monkeypatch.setattr(TerraFormer, 'MAX_FILE_SIZE', 5)
            TestIt('quilo')


def test_rename(embed_data, line_tester):
    from zerotk.easyfs import GetFileContents

    def Doit(lines):
        source = ''.join([i + '\n' for i in lines])

        terra = TerraFormer(source=source)
        changed = terra.ReorganizeImports(
            refactor={
                'StringIO.StringIO': 'io.StringIO',
                'cStringIO.StringIO': 'io.StringIO',
                'cStringIO': 'from io.StringIO',
                'StringIO': 'from io.StringIO',
            }
        )
        if changed:
            for i_symbol in terra.module.Walk():
                if i_symbol.PREFIX == 'USE' and i_symbol.name in ('cStringIO.StringIO', 'StringIO.StringIO'):
                    i_symbol.Rename('StringIO')

        return terra.GenerateSource().splitlines()

    line_tester.TestLines(
        GetFileContents(embed_data['rename.txt'], encoding='UTF-8'),
        Doit,
    )


def testSymbolVisitor():

    def PrintScopes(scopes):
        result = []
        for i in sorted(scopes, key=lambda x:x.name):
            result.append('- %s' % i)
            for j in sorted(i.uses):
                result.append('  - %s' % j)
        return '\n'.join(result)

    source_code = dedent(
        '''
        from alpha import Alpha
        import coilib50

        class Zulu(Alpha):
            """
            Zulu class docs.
            """

            def __init__(self, name):
                """
                Zulu.__init__ docs.
                """
                self._name = name
                alpha = bravo
                coilib50.Charlie()
                f = coilib50.Delta(echo, foxtrot)
        '''
    )

    from zerotk.terraformer._visitor import ASTVisitor
    code = TerraFormer._Parse(source_code)
    visitor = ASTVisitor()
    visitor.Visit(code)

    assert visitor._module.AsString() == dedent(
        '''
            module (1, 0) module
              IMPORT-BLOCK (1, 0) import-block #0
                IMPORT-FROM (0, 0) alpha
                  IMPORT (1, 0) alpha.Alpha
                IMPORT (2, 0) coilib50
              USE (3, 0) Alpha
              class (0, 0) Zulu
                def (8, 4) __init__
                  ARG (9, 17) self
                  ARG (9, 23) name
                  DEF (13, 8) self._name
                  USE (13, 21) name
                  DEF (14, 8) alpha
                  USE (14, 16) bravo
                  USE (15, 8) coilib50.Charlie
                  DEF (16, 8) f
                  USE (16, 12) coilib50.Delta
                  USE (16, 27) echo
                  USE (16, 33) foxtrot
        '''
    )

    # Compares the results with the one given by compiler.symbols.SymbolVisitor, our inspiration.
    from compiler.symbols import SymbolVisitor
    from compiler.transformer import parse
    from compiler.visitor import walk

    code = parse(source_code)
    symbol_visitor = SymbolVisitor()
    walk(code, symbol_visitor)

    assert PrintScopes(symbol_visitor.scopes.values()) == dedent(
        '''
            - <ClassScope: Zulu>
            - <FunctionScope: __init__>
              - bravo
              - coilib50
              - echo
              - foxtrot
              - name
              - self
            - <ModuleScope: global>
              - Alpha
          '''
    )



#===================================================================================================
# Fixture line_tester
#===================================================================================================
class LineTester(object):

    def _Fail(self, obtained, expected):
        import difflib

        diff = [i for i in difflib.context_diff(obtained, expected)]
        diff = '\n'.join(diff)
        raise AssertionError(diff)


    def TestLines(self, doc, processor):
        from zerotk.reraiseit import reraise

        lines = doc.split('\n')
        input_ = []
        expected = []
        stage = 'input'
        for i_line in lines:
            if i_line.strip() == '---':
                stage = 'output'
                continue
            if i_line.strip() == '===':
                try:
                    obtained = processor(input_)
                except Exception as exception:
                    reraise(exception, 'While processing lines::\n  %s\n' % '\n  '.join(input_))
                if obtained != expected:
                    self._Fail(obtained, expected)
                input_ = []
                expected = []
                stage = 'input'
                continue

            if stage == 'input':
                input_.append(i_line)
            else:
                expected.append(i_line)

        if input_:
            obtained = processor(input_)
            if obtained != expected:
                self._Fail(obtained, expected)


@pytest.fixture
def line_tester():
    return LineTester()


def testLineTester(line_tester):

    def Doit(lines):
        return ['(%s)' % i for i in lines]

    def RaiseException(lines):
        raise TypeError()

    line_tester.TestLines('===\nalpha\n---\n(alpha)', Doit)

    line_tester.TestLines('===\nalpha\n\n\n---\n(alpha)\n()\n()', Doit)

    with pytest.raises(AssertionError):
        line_tester.TestLines('===\nalpha\n---\nERROR\n===\nalpha\n---\n(alpha)', Doit)

    with pytest.raises(AssertionError):
        line_tester.TestLines('===\nalpha\n---\nERROR', Doit)

    with pytest.raises(Exception) as excinfo:
        line_tester.TestLines('===\nalpha\n\n\n---\n(alpha)\n()\n()', RaiseException)
    assert "While processing lines::" in str(excinfo.value)
