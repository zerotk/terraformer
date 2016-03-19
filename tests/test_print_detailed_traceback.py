# coding: UTF-8
from __future__ import unicode_literals

from pypugly.text import dedent
from zerotk.easyfs import CreateFile
from zerotk.terraformer.print_detailed_traceback import PrintDetailedTraceback
from io import BytesIO, StringIO
import itertools
import mock
import pytest
import re
import sys


def testPrintDetailedTraceback(embed_data):

    def Pad(seq):
        """Pads a sequence of strings with up to 4 leading '0' chars"""
        result = []
        for value in seq:
            try:
                result.append('0' * (4 - len(value)) + value)
            except TypeError:
                # we raise our own exception because the message changes between python versions
                raise TypeError("object of type 'int' has no len()")
        return result

    data = map(unicode, xrange(100))
    data[3] = 3

    stream = StringIO()
    try:
        Pad(data)
    except:
        PrintDetailedTraceback(max_levels=2, stream=stream, max_line_width=100)
    else:
        assert False, 'Pad() should fail with an exception!'

    ss = stream.getvalue()

    # >>> Remove parts of the string that are platform/file system dependent

    # remove filename
    filename_re = re.compile(re.escape(__file__) + '?', re.IGNORECASE)
    ss = re.sub(filename_re, '/path_to_file/file.py', ss)

    # remove address of objects
    address_re = re.compile('at 0x([a-f0-9]+)', re.IGNORECASE)
    ss = re.sub(address_re, 'at 0x0', ss)

    # "self" description because the name of the module changes if we run this test
    # from the command line vs running it with runtests
    self_re = re.compile('self = <.*>', re.IGNORECASE)
    ss = re.sub(self_re, 'self = <Test.testPrintDetailedTraceback>', ss)

    obtained_filename = embed_data['traceback.obtained.txt']
    CreateFile(obtained_filename, ss)

    # Changes
    # File "/path_to_file/file.py", line 51, in testPrintDetailedTraceback
    # to:
    # File "/path_to_file/file.py", line XX, in testPrintDetailedTraceback
    def FixIt(lines):
        import re
        return [re.sub('line (\\d)+', 'line XX', i) for i in lines]

    embed_data.assert_equal_files(
        obtained_filename,
        'traceback.expected.txt',
        fix_callback=FixIt
    )


# def testPrintDetailedTracebackNotAsciiPath(embed_data, unicode_samples, script_runner):
#     SCRIPT = dedent(
#         '''
#         # coding: UTF-8
#         from zerotk.terraformer.print_detailed_traceback import PrintDetailedTraceback
#         import io
#         try:
#             assert False
#         except:
#             PrintDetailedTraceback(stream=io.StringIO())
#             print 'COMPLETE'
#         '''
#     )
#     script_name = embed_data.GetDataFilename('%s/script.py_' % unicode_samples.UNICODE_PREFERRED_LOCALE)
#     obtained = script_runner.ExecuteScript(script_name, SCRIPT)
#     assert obtained == 'COMPLETE'


def testNoException():
    '''
    Should not print anything in case there's no exception info (complies with the behavoir from
    traceback.print_exception)
    '''
    # "Old", non-io StringIO: doesn't perform typechecks when writing. Since when there's no
    # exception the code falls back to traceback.print_exception, the stream must be able to
    # accept bytes.
    stream = StringIO()
    PrintDetailedTraceback(exc_info=(None, None, None), stream=stream)
    assert stream.getvalue() == 'None\n'


def testWrongStreamType():
    '''
    Test whether old-style streams correctly raise assertion errors.
    '''
    import StringIO as OldStringIO
    import cStringIO

    for stream in [cStringIO.StringIO(), OldStringIO.StringIO()]:
        with pytest.raises(AssertionError):
            PrintDetailedTraceback(exc_info=(None, None, None), stream=stream)


@pytest.mark.parametrize(('exception_message',), [(u'fake unicode message',), (u'Сообщение об ошибке.',)])
def testPrintDetailedTracebackWithUnicode(exception_message):
    '''
    Test PrintDetailedTraceback with 'plain' unicode arguments and an unicode argument with cyrillic
    characters
    '''

    stream = StringIO()
    try:
        raise Exception(exception_message)
    except:
        PrintDetailedTraceback(stream=stream)

    assert 'Exception: %s' % (exception_message) in stream.getvalue()


@pytest.mark.parametrize('exception_message, stream_encoding', itertools.product(
    ['fake unicode message', 'Сообщение об ошибке.'],
    [None, b'ascii', b'utf-8'],
))
def testPrintDetailedTracebackToFakeStderr(exception_message, stream_encoding, fake_stderr):
    '''
    Test PrintDetailedTraceback with 'plain' unicode arguments and an unicode argument with cyrillic
    characters, written to a buffer similar to PrintDetailedTraceback()'s default stream,
    sys.std_err.
    '''
    fake_stderr.encoding = stream_encoding

    try:
        raise Exception(exception_message)
    except:
        with mock.patch.object(sys, 'stderr', new=fake_stderr):
            PrintDetailedTraceback(stream=fake_stderr)

    if stream_encoding is None:
        # std streams may have None as encoding. PrintDetailedTraceback should use utf-8 as default.
        stream_encoding = 'utf-8'
    _AssertEncodedMessageIsInStreamOutput(fake_stderr, exception_message, stream_encoding)


def _AssertEncodedMessageIsInStreamOutput(stream, exception_message, stream_encoding):
    written_traceback = stream.getvalue()
    encoded_message = exception_message.encode(stream_encoding, errors='replace')
    assert b'Exception: %s' % encoded_message in written_traceback


@pytest.mark.parametrize(('exception_message',), [(u'fake unicode message',), (u'Сообщение об ошибке.',)])
def testPrintDetailedTracebackToFakeStderrWhenStreamHasNoEncodingAttribute(exception_message, fake_stderr):
    '''
    PrintDetailedTraceback must not rely on an encoding attribute being present.
    '''
    assert not hasattr(fake_stderr, 'encoding')

    try:
        raise Exception(exception_message)
    except:
        with mock.patch.object(sys, 'stderr', new=fake_stderr):
            PrintDetailedTraceback(stream=fake_stderr)

    _AssertEncodedMessageIsInStreamOutput(fake_stderr, exception_message, 'utf-8')


@pytest.mark.parametrize(('exception_message',), [(u'fake unicode message',), (u'Сообщение об ошибке.',)])
def testPrintDetailedTracebackToRealStderr(exception_message):
    '''
    The same as above, but writing to the real stderr. Just a smoke test to verify that no errors
    occur.
    '''
    try:
        raise Exception(exception_message)
    except:
        PrintDetailedTraceback()


def testOmitLocals():
    '''
    Makes sure arguments and local variables are not present in traceback contents whenever
    omit locals option is enabled.
    '''
    stream = StringIO()
    def Flawed(foo):
        arthur = 'dent'  # @UnusedVariable
        raise Exception('something')

    try:
        Flawed(foo='bar')
    except:
        PrintDetailedTraceback(stream=stream, omit_locals=True)

    stream_value = stream.getvalue()
    assert 'foo' not in stream_value
    assert 'bar' not in stream_value
    assert 'arthur' not in stream_value
    assert 'dent' not in stream_value


@pytest.fixture
def fake_stderr(monkeypatch):
    '''
    Create a stream to replace stderr.
    '''
    # Since we want to check the values written, create a 'fake_stderr' that is simple a BytesIO
    # with the same expected encoding as sys.std_err's encoding.
    fake_stderr = BytesIO()
    return fake_stderr
