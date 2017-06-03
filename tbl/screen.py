from   bisect import *
from   contextlib import contextmanager
import curses
import functools
import logging
import sys

#-------------------------------------------------------------------------------

class Model(object):
    # FIXME: Interim.

    class Col(object):

        def __init__(self, name, arr):
            self.name = name
            self.arr = arr


    def __init__(self, cols):
        self.num_col = len(cols)
        if self.num_col == 0:
            self.num_row = 0
        else:
            self.num_row = len(cols[0].arr)
            assert all( len(c.arr) == self.num_row for c in cols )
        self.cols = cols



def choose_fmt(arr):
    width = max( len(str(a)) for a in arr )
    fmt = lambda v: str(v)[: width] + " " * (width - len(str(v)[: width]))
    fmt.width = width
    return fmt


class State(object):
    # FIXME: Interim.

    def __init__(self, model):
        num_columns = len(model.cols)
        self.vis = [True] * num_columns
        self.fmt = [ choose_fmt(c.arr) for c in model.cols ]
        self.row = 0
        self.x = 0
        self.left_border    = "\u2551 "
        self.separator      = " \u2502 "
        self.right_border   = " \u2551"



#-------------------------------------------------------------------------------

def lay_out_cols(model, state):
    """
    Computes column layout.

    @return
      A sequence of `[x, item]` pairs describing layout, where `x` is the
      column position and `item` is either a column index from the model or
      a string literal.
    """
    layout = []
    x0 = 0

    if state.left_border:
        layout.append([x0, state.left_border])
        x0 += len(state.left_border)

    first_col = True

    for i in range(model.num_col):
        if not state.vis[i]:
            # Not visibile.
            continue
        
        if first_col:
            first_col = False
        elif state.separator:
            layout.append([x0, state.separator])
            x0 += len(state.separator)

        fmt = state.fmt[i]
        layout.append([x0, i])
        x0 += fmt.width

    if state.right_border:
        layout.append([x0, state.right_border])
        x0 += len(state.right_border)

    return layout


def render(win, model, state):
    """
    Renders `model` with view `state` in curses `win`.
    """
    # Compute the column layout.
    layout = lay_out_cols(model, state)

    max_y, max_x = win.getmaxyx()

    # Truncate to window size and position.
    layout_x = [ x for x, _ in layout ]
    i0 = bisect_right(layout_x, state.x) - 1
    i1 = bisect_left(layout_x, state.x + max_x)
    layout = [ (x - state.x, l) for x, l in layout[i0 : i1] ]

    # Now, draw.
    rows = min(max_y - 1, model.num_row - state.row)
    for r in range(rows):
        win.move(r, 0)
        for x, v in layout:
            if isinstance(v, int):
                v = state.fmt[v](model.cols[v].arr[state.row + r])
            
            if x < 0:
                v = v[-x :]
            if x + len(v) >= max_x:
                v = v[: max_x - x]

            win.addstr(v)


def advance_column(model, state, forward=True):
    layout = lay_out_cols(model, state)
    # Select columns only.
    xs = [ x for x, i in layout if isinstance(i, int) ]

    if forward:
        return xs[min(bisect_right(xs, state.x), len(xs) - 1)]
    else:
        return xs[max(bisect_right(xs, state.x - 1) - 1, 0)]
    


@contextmanager
def curses_screen():
    """
    Curses context manager.

    Returns the screen window on entry.  Restores the terminal state on exit.
    """
    stdscr = curses.initscr()
    curses.noecho()
    stdscr.keypad(True)
    curses.cbreak()
    curses.curs_set(False)

    try:
        yield stdscr
    finally:
        curses.curs_set(True)
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


#-------------------------------------------------------------------------------

def load_test(path):
    import csv
    with open(path) as file:
        reader = csv.reader(file)
        rows = iter(reader)
        names = next(rows)
        arrs = zip(*list(rows))
    model = Model([ Model.Col(n, a) for n, a in zip(names, arrs) ])
    state = State(model)
    return model, state


def main():
    logging.basicConfig(filename="log", level=logging.INFO)

    model, state = load_test(sys.argv[1])

    with curses_screen() as stdscr:
        render(stdscr, model, state)
        stdscr.refresh()

        while True:
            c = stdscr.getch()
            logging.info("getch() -> {!r}".format(c))
            if c == curses.KEY_LEFT:
                state.x = advance_column(model, state, forward=False)
            elif c == curses.KEY_SLEFT:
                if state.x > 0:
                    state.x -= 1
            elif c == curses.KEY_RIGHT:
                state.x = advance_column(model, state, forward=True)
            elif c == curses.KEY_SRIGHT:
                state.x += 1
            elif c == curses.KEY_UP:
                if state.row > 0:
                    state.row -= 1
            elif c == curses.KEY_DOWN:
                if state.row < model.num_row - 1:
                    state.row += 1
            elif c == ord('q'):
                break
            else:
                continue
            stdscr.erase()
            render(stdscr, model, state)
            stdscr.refresh()



if __name__ == "__main__":
    main()

