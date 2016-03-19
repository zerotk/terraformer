from __future__ import unicode_literals
import locale
import six



#===================================================================================================
# ExceptionToUnicode
#===================================================================================================
def ExceptionToUnicode(exception):
    '''
    Obtains unicode representation of an Exception.

    This wrapper is used to circumvent Python 2.7 problems with built-in exceptions with unicode
    messages.

    Steps used:
        * Try to obtain Exception.__unicode__
        * Try to obtain Exception.__str__ and decode with utf-8
        * Try to obtain Exception.__str__ and decode with locale.getpreferredencoding
        * If all fails, return Exception.__str__ and decode with (ascii, errors='replace')

    :param Exception exception:

    :return unicode:
        Unicode representation of an Exception.
    '''
    try:
        # First, try to obtain __unicode__ as defined by the Exception
        return unicode(exception)
    except UnicodeDecodeError:
        try:
            # If that fails, try decoding with utf-8 which is the strictest and will complain loudly.
            return bytes(exception).decode('utf-8')
        except UnicodeDecodeError:
            try:
                # If that fails, try obtaining bytes repr and decoding with locale
                return bytes(exception).decode(locale.getpreferredencoding())
            except UnicodeDecodeError:
                # If all failed, give up and decode with ascii replacing errors.
                return bytes(exception).decode(errors='replace')
    except UnicodeEncodeError:
        # Some exception contain unicode messages, but try to convert them to bytes when calling
        # unicode() (such as IOError). In these cases, we do our best to fix Python 2.7's poor
        # handling of unicode exceptions.
        assert type(exception.message) == unicode  # This should be true if code got here.
        return exception.message
