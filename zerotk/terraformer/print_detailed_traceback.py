from __future__ import unicode_literals
import locale
import sys



#===================================================================================================
# _StreamWrapper
#===================================================================================================
import six


class _StreamWrapper(object):
    """
    A simple wrapper to decode bytes into unicode objects before writing to an unicode-only stream.
    """
    def __init__(self, stream, encoding):
        self.stream = stream
        self.encoding = encoding

    def write(self, value):
        self.stream.write(value.decode(self.encoding))


#===================================================================================================
# PrintDetailedTraceback
#===================================================================================================
def PrintDetailedTraceback(exc_info=None, stream=None, max_levels=None, max_line_width=120, omit_locals=False):
    """
    Prints a more detailed traceback than Python's original one showing, for each frame, also the
    locals at that frame and their values.

    :type exc_info: (type, exception, traceback)
    :param exc_info:
        The type of the exception, the exception instance and the traceback object to print. Exactly
        what is returned by sys.exc_info(), which is used if this param is not given.

    :type stream: file-like object
    :param stream:
        File like object to print the traceback to. Note that the traceback will be written directly
        as unicode to the stream, unless the stream is either sys.stderr or sys.stdout. If no stream
        is passed, sys.stderr is used.

    :param int max_levels:
        The maximum levels up in the traceback to display. If None, print all levels.

    :param int max_line_width:
        The maximum line width for each line displaying a local variable in a stack frame. Each
        line displaying a local variable will be truncated at the middle to avoid cluttering
        the display;

    :param bool omit_locals:
        If true it will omit function arguments and local variables from traceback. It is an option
        especially interesting if an error during a function may expose sensitive data, like an user
        private information as a password. Defaults to false as most cases won't be interested in
        this feature.
    """
    from zerotk.terraformer.exceptions import ExceptionToUnicode
    from zerotk.terraformer.klass import IsInstance
    import io
    import locale

    if six.PY2:
        import StringIO
        import cStringIO
        string_io_types = (StringIO.StringIO, cStringIO.OutputType)
    else:
        import io
        string_io_types = (io.StringIO)

    assert not IsInstance(stream, string_io_types), \
        'Old-style StringIO passed to PrintDetailedTraceback()'

    # For sys.stderr and sys.stdout, we should encode the unicode objects before writing.
    def _WriteToEncodedStream(message):
        assert type(message) is six.text_type
        encoding = getattr(stream, 'encoding', None)
        stream.write(message.encode(encoding or 'utf-8', errors='replace'))

    def _WriteToUnicodeStream(message):
        assert type(message) is six.text_type
        stream.write(message)

    if stream is None:
        stream = sys.stderr


    if stream in (sys.stderr, sys.stdout):
        _WriteToStream = _WriteToEncodedStream
        wrapped_stream = stream
    else:
        _WriteToStream = _WriteToUnicodeStream
        encoding = locale.getpreferredencoding()
        wrapped_stream = _StreamWrapper(stream, encoding)


    if exc_info is None:
        exc_info = sys.exc_info()

    exc_type, exception, tb = exc_info

    if exc_type is None or tb is None:
        # if no exception is given, or no traceback is available, let the print_exception deal
        # with it. Since our stream deals with unicode, wrap it
        import traceback
        traceback.print_exception(exc_type, exception, tb, max_levels, wrapped_stream)
        return

    # find the bottom node of the traceback
    while True:
        if not tb.tb_next:
            break
        tb = tb.tb_next

    # obtain the stack frames, up to max_levels
    stack = []
    f = tb.tb_frame
    levels = 0
    while f:
        stack.append(f)
        f = f.f_back
        levels += 1
        if max_levels is not None and levels >= max_levels:
            break
    stack.reverse()

    _WriteToStream('Traceback (most recent call last):\n')

    encoding = locale.getpreferredencoding()
    for frame in stack:
        params = dict(
            name=frame.f_code.co_name.decode(encoding),
            filename=frame.f_code.co_filename.decode(encoding),
            lineno=frame.f_lineno,
        )

        _WriteToStream('  File "%(filename)s", line %(lineno)d, in %(name)s\n' % params)

        try:
            lines = io.open(frame.f_code.co_filename).readlines()
            line = lines[frame.f_lineno - 1]
        except:
            pass  # don't show the line source
        else:
            _WriteToStream('    %s\n' % line.strip())

        if not omit_locals:
            # string used to truncate string representations of objects that exceed the maximum
            # line size
            trunc_str = '...'
            for key, value in sorted(frame.f_locals.iteritems()):
                ss = '            %s = ' % key
                # be careful to don't generate any exception while trying to get the string
                # representation of the value at the stack, because raising an exception here
                # would shadow the original exception
                try:
                    val_repr = repr(value).decode(encoding)
                except:
                    val_repr = '<ERROR WHILE PRINTING VALUE>'
                else:
                    # if the val_pre exceeds the maximium size, we truncate it in the middle
                    # using trunc_str, showing the start and the end of the string:
                    # "[1, 2, 3, 4, 5, 6, 7, 8, 9]" -> "[1, 2, ...8, 9]"
                    if len(ss) + len(val_repr) > max_line_width:
                        space = max_line_width - len(ss) - len(trunc_str)
                        middle = int(space / 2)
                        val_repr = val_repr[:middle] + trunc_str + val_repr[-(middle + len(trunc_str)):]

                _WriteToStream(ss + val_repr + '\n')

    message = ExceptionToUnicode(exception)

    _WriteToStream('%s: %s\n' % (exc_type.__name__, message))

