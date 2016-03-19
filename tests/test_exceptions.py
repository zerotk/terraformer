# coding: UTF-8
from __future__ import unicode_literals
from zerotk.terraformer.exceptions import ExceptionToUnicode
import locale
import pytest
import sys



def testExceptionToUnicode(exception_message, lpe_exception_message, fse_exception_message):
    assert ExceptionToUnicode(Exception(exception_message)) == exception_message
    assert ExceptionToUnicode(Exception(fse_exception_message)) == exception_message
    assert ExceptionToUnicode(Exception(lpe_exception_message)) == exception_message



def testExceptionToUnicodeOSError(exception_message, lpe_exception_message, fse_exception_message):
    assert ExceptionToUnicode(OSError(2, exception_message)) == '[Errno 2] ' + exception_message
    assert ExceptionToUnicode(OSError(2, fse_exception_message)) == '[Errno 2] ' + exception_message
    assert ExceptionToUnicode(OSError(2, lpe_exception_message)) == '[Errno 2] ' + exception_message



def testExceptionToUnicodeIOError(exception_message, lpe_exception_message, fse_exception_message):
    # IOError is really stupid, unicode(IOError('á')) actually raises UnicodeEncodeError
    # (not UnicodeDecodeError!)
    assert ExceptionToUnicode(IOError(exception_message)) == exception_message
    assert ExceptionToUnicode(IOError(fse_exception_message)) == exception_message
    assert ExceptionToUnicode(IOError(lpe_exception_message)) == exception_message



def testExceptionToUnicodeCustomException(exception_message, lpe_exception_message, fse_exception_message):
    class MyException(Exception):
        def __unicode__(self):
            return 'hardcoded unicode repr'
    assert ExceptionToUnicode(MyException(exception_message)) == 'hardcoded unicode repr'



def testExceptionToUnicodeBadEncoding(exception_message, lpe_exception_message, fse_exception_message):
    assert ExceptionToUnicode(Exception(b'random \x90\xa1\xa2')) == 'random \ufffd\ufffd\ufffd'


def testExceptionToUnicodeUTF8():
    assert ExceptionToUnicode(Exception(b'Ação')) == 'Ação'


#===================================================================================================
# Fixtures
#===================================================================================================
@pytest.fixture
def exception_message():
    exception_message = 'кодирование'
    # Use another message if this machine's locale does not support cyrilic
    try:
        exception_message.encode(locale.getpreferredencoding())
    except UnicodeEncodeError:
        exception_message = 'látïn-1'

    return exception_message


@pytest.fixture
def lpe_exception_message(exception_message):
    return exception_message.encode(locale.getpreferredencoding())


@pytest.fixture
def fse_exception_message(exception_message):
    return exception_message.encode(sys.getfilesystemencoding())
