# coding: UTF-8
from __future__ import unicode_literals

from zerotk.easyfs import CreateFile, GetFileContents
from zerotk.terraformer.tf_script import app
from zerotk.text import dedent


def testDocs():
    """
    Test "tf" API by printing the general documentation.
    """

    app.TestScript(
        dedent(
            """
                >terraformer

                Usage:
                    terraformer <subcommand> [options]

                Commands:
                    symbols             List all symbols in the given python source code. Currently only lists IMPORTS.
                    fix-format          Perform the format fixes on sources files, including tabs, eol, eol-spaces and imports.
                    add-import-symbol   Adds an import-symbol in all files.
                    fix-commit          Perform the format fixes on sources files on a git repository modified files.
                    fix-is-frozen       Fix some pre-determinated set of symbols usage with the format:
                    fix-encoding        Fix python module files encoding, converting all non-ascii encoded files to UTF-8.
                    fix-stringio        Fix StringIO usage.

            """
        )
    )


def testSymbols(embed_data):
    """
    Test tf symbols command.
    This command is a WIP and should grow as "tf" interprets more and more symbols from python
    modules.
    """

    filename = embed_data['testSymbols.py_']
    original = """
        import alpha

        class Alpha(object):

            def Method(self):
                pass

        def Function():
            pass

    """
    assert CreateFile(filename, dedent(original), encoding='UTF-8')

    app.TestScript(
        dedent(
            """
                >terraformer symbols %(filename)s
                1: IMPORT alpha
            """ % locals()
        )
    )


def testFixFormat(embed_data):
    """
    General test for tbe "tf fix-format" command.
    This is a smoke test for the command interaction since most of the real
    testing is done on pytest_terra_former.py
    """

    filename = embed_data['testFixFormat.py']
    data_dir = embed_data.get_data_dir()
    original = """
        import zulu
        from bravo import Bravo
        import alpha

        class Alpha(object):

            def Method(self):
                pass

        def Function():
            pass

    """
    assert CreateFile(filename, dedent(original), encoding='UTF-8')

    app.TestScript(
        dedent(
            """
                >terraformer fix-format --single-job %(data_dir)s
                - %(filename)s: FIXED

            """ % locals()
        )
    )
    assert GetFileContents(filename, encoding='UTF-8') == dedent(
        """
            from bravo import Bravo
            import alpha
            import zulu

            class Alpha(object):

                def Method(self):
                    pass

            def Function():
                pass

        """
    )


def test_fix_format_error(embed_data):
    """
    Check _FixFormat error output (detailed traceback).
    """
    filename = embed_data['test_fix_format_error.py']
    data_dir = embed_data.get_data_dir()
    original = """
        import zulu
        from bravo import Bravo
        import alpha

        class Alpha(object):

            def Method(self)
                pass

        def Function():
            pass

    """
    assert CreateFile(filename, dedent(original), encoding='UTF-8')

    app.TestScript(
        dedent(
            """
                >>>terraformer fix-format --single-job --traceback-limit=0 %(data_dir)s
                - %(filename)s: ERROR:
                \b\b
                On TerraForming.ReorganizeImports with filename: %(filename)s
                Had problems parsing:
                > import zulu
                > from bravo import Bravo
                > import alpha
                >\b
                > class Alpha(object):
                >\b
                >     def Method(self)
                >         pass
                >\b
                > def Function():
                >     pass


                bad input: type=4, value=u'\\r\\n', context=('', (7, 20))
                --- * ---
            """ % locals()
        ).replace('\b', ' '),
        input_prefix='>>>'
    )
    assert GetFileContents(filename, encoding='UTF-8') == dedent(
        """
            import zulu
            from bravo import Bravo
            import alpha

            class Alpha(object):

                def Method(self)
                    pass

            def Function():
                pass

        """
    )


def testAddImportSymbol(embed_data):
    """
    General test for the "tf add-import-symbol" command.
    """
    filename = embed_data['testFixFormat.py']
    data_dir = embed_data.get_data_dir()

    original = """
        import zulu
        from bravo import Bravo
        import alpha

        class Alpha(object):

            def Method(self):
                pass

        def Function():
            pass

    """
    assert CreateFile(filename, dedent(original), encoding='UTF-8')

    app.TestScript(
        dedent(
            """
                >terraformer add-import-symbol --single-job "__future__.unicode_literals" %(filename)s
                - %(filename)s: FIXED
            """ % locals()
        )
    )

    assert GetFileContents(filename, encoding='UTF-8') == dedent(
        """
            from __future__ import unicode_literals
            from bravo import Bravo
            import alpha
            import zulu

            class Alpha(object):

                def Method(self):
                    pass

            def Function():
                pass

        """
    )


def testFixEncoding(embed_data):
    """
    General test for tbe "tf fix-encoding" command.
    """

    def TestFixEncoding(original, expected, encoding, lineno=0):
        filename = embed_data['testFixEncoding.py_']

        assert CreateFile(
            filename,
            dedent(original),
            encoding=encoding
        )

        app.TestScript(
            dedent(
                """
                    >terraformer fix-encoding %(filename)s
                    - %(filename)s: %(encoding)s (line:%(lineno)s)

                """ % locals()
            )
        )

        obtained = GetFileContents(filename, encoding='UTF-8')
        assert obtained == dedent(expected)

    TestFixEncoding(
        """
            from __future__ import with_statement
            # coding: latin1
            import sys

            action = 'ação'
        """,
        """
            # coding: UTF-8
            from __future__ import with_statement
            import sys

            action = 'ação'
        """,
        'latin1',
        lineno=1
    )

    TestFixEncoding(
        """
            # coding: cp1252
            import alpha
            import bravo

            action = 'ação'
        """,
        """
            # coding: UTF-8
            import alpha
            import bravo

            action = 'ação'
        """,
        'cp1252'
    )

    # Support "coding=".
    TestFixEncoding(
        """
            # coding=UTF-8
            import alpha
            import bravo

            action = 'ação'
        """,
        """
            # coding: UTF-8
            import alpha
            import bravo

            action = 'ação'
        """,
        'UTF-8'
    )


def testFixIsFrozen(embed_data):
    """
    General test for tbe "tf is-frozen" command.
    """

    filename = embed_data['testFixIsFrozen.py']
    data_dir = embed_data.get_data_dir()
    original = """
        import coilib50
        from coilib50.basic import property

        if coilib50.IsFrozen():
            print "Frozen"
            property.Create('')

    """
    assert CreateFile(filename, dedent(original), encoding='UTF-8')

    app.TestScript(
        dedent(
            """
                >terraformer fix-is-frozen %(filename)s
                - %(filename)s

            """ % locals()
        )
    )
    assert GetFileContents(filename, encoding='UTF-8') == dedent(
        """
        from ben10 import property_
        from ben10.foundation.is_frozen import IsFrozen
        import coilib50
        from coilib50.basic import property

        if IsFrozen():
            print "Frozen"
            property_.Create('')

        """
    )
