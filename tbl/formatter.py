from   fixfmt.npfmt import choose_formatter

from   .commands import command

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
        elif fmt.precision == 0:
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


