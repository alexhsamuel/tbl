from   __future__ import absolute_import, division, print_function, unicode_literals

import functools
from   six.moves import range
import sys

import logging
logging.basicConfig(filename="log", level=logging.INFO)

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
        self.x = 0



#-------------------------------------------------------------------------------

import csv
import curses

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


def first_idx(items, pred):
    for i, item in enumerate(items):
        if pred(item):
            return i
    else:
        return None


def render(win, model, state):
    sep = " | "

    max_y, max_x = win.getmaxyx()

    # Determine the first and last columns we need to show, and how much
    # to truncate them.
    x0 = -state.x
    i0 = 0
    for i, (fmt, vis) in enumerate(zip(state.fmt, state.vis)):
        if not vis:
            continue
        x1 = x0 + fmt.width + len(sep)
        logging.info("x0={} x1={} width={}".format(x0, x1, fmt.width))
        if x1 <= 0:
            # This column is fully off the left edge.
            logging.info("off left")
            x0 = x1
            continue

        if x0 <= 0:
            # First column: partially off the left edge.
            i0 = i
            t0 = -x0
            x0 = 0
            logging.info("left trunc: {} {}".format(i0, t0))
        if max_x <= x1:
            # Last column: partially off the right edge.  
            t1 = max_x - x0
            i1 = i + 1
            logging.info("right trunc: {} {}".format(i1, t1))
            break
        x0 = x1

    win.erase()
    for r in range(min(max_y - 1, model.num_row)):
        win.move(r, 0)
        for i in range(i0, i1):
            if not state.vis[i]:
                continue
            val = state.fmt[i](model.cols[i].arr[r]) + sep
            if i == i0:
                val = val[t0 :]
            if i == i1 - 1:
                val = val[: t1]
            win.addstr(val)
    win.refresh()


def main():
    stdscr = curses.initscr()
    curses.noecho()
    stdscr.keypad(True)
    curses.cbreak()
    curses.curs_set(False)

    try:
        model, state = load_test(sys.argv[1])
        render(stdscr, model, state)
        while True:
            c = stdscr.getch()
            logging.info("getch() -> {!r}".format(c))
            if c == ord('j'):
                if state.x > 0:
                    state.x -= 1
            elif c == ord('J'):
                if state.x >= 8:
                    state.x -= 8
            elif c == ord('k'):
                state.x += 1
            elif c == ord('K'):
                state.x += 8
            elif c == ord('q'):
                break
            else:
                continue
            render(stdscr, model, state)
    finally:
        curses.curs_set(True)
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()



if __name__ == "__main__":
    main()

