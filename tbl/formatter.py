import logging

from   .commands import command, CmdError, CmdResult

#-------------------------------------------------------------------------------

try:
    from fixfmt.numpy import choose_formatter

except ImportError:
    # Not available.
    logging.warning("fixfmt not available")

    def choose_formatter(arr, min_width=0):
        width = max(min_width, max( len(str(a)) for a in arr ))
        fmt = lambda v: str(v)[: width] + " " * (width - len(str(v)[: width]))
        fmt.width = width
        return fmt

#-------------------------------------------------------------------------------

@command()
def decrease_column_width(vw):
    fmt = vw.cols[vw.cur.c].fmt
    try:
        if fmt.size > 1:
            fmt.size -= 1
    except AttributeError:
        pass


@command()
def increase_column_width(vw):
    fmt = vw.cols[vw.cur.c].fmt
    try:
        fmt.size += 1
    except AttributeError:
        pass


@command()
def decrease_column_precision(vw):
    fmt = vw.cols[vw.cur.c].fmt
    try:
        if fmt.precision is None:
            pass
        elif fmt.precision is 0:
            fmt.precision = None
        else:
            fmt.precision -= 1
    except AttributeError:
        pass


@command()
def increase_column_precision(vw):
    fmt = vw.cols[vw.cur.c].fmt
    try:
        if fmt.precision is None:
            fmt.precision = 0
        else:
            fmt.precision += 1
    except AttributeError:
        pass


