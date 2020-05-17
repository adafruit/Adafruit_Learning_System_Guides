def wrap_nicely(string, max_chars):
    """ From: https://www.richa1.com/RichardAlbritton/circuitpython-word-wrap-for-label-text/
    A helper that will return the string with word-break wrapping.
    :param str string: The text to be wrapped.
    :param int max_chars: The maximum number of characters on a line before wrapping.
    """
    string = string.replace('\n', '').replace('\r', '') # strip confusing newlines
    words = string.split(' ')
    the_lines = []
    the_line = ""
    for w in words:
        if len(the_line+' '+w) <= max_chars:
            the_line += ' '+w
        else:
            the_lines.append(the_line)
            the_line = w
    if the_line:
        the_lines.append(the_line)
    the_lines[0] = the_lines[0][1:]
    the_newline = ""
    for w in the_lines:
        the_newline += '\n'+w
    return the_newline
