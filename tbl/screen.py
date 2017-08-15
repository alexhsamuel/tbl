from   contextlib import contextmanager
import curses
import curses.textpad
import functools
from   functools import partial
import logging
import numpy as np
import os
import sys

from   . import controller, io, keymap, model, view
from   .commands import *
from   .curses_keyboard import get_key
from   .lib import log
from   .text import pad, palide
import curses.textpad

#-------------------------------------------------------------------------------
# Curses setup

@contextmanager
def curses_screen():
    """
    Curses context manager.

    Returns the screen window on entry.  Restores the terminal view on exit.
    """
    # Disable the curses ESC translation delay.
    # FIXME: It might be possible to set the ESCDELAY variable in libncurses.so
    # directly with ctypes.
    os.environ["ESCDELAY"] = "0"

    win = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(False)
    curses.raw()

    win.keypad(True)
    win.notimeout(True)
    win.nodelay(True)

    # Enable mouse events.
    mouse_mask = curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED
    new_mask, _ = curses.mousemask(mouse_mask)
    if new_mask != mouse_mask:
        logging.warning(
            "problem with mouse support: {:x} {:x}"
            .format(mouse_mask, new_mask))

    init_attrs()

    try:
        yield win
    finally:
        win.nodelay(False)
        win.notimeout(False)
        win.keypad(False)

        curses.noraw()
        curses.curs_set(True)
        curses.nocbreak()
        curses.echo()
        curses.endwin()


class Attrs:

    pass



def init_attrs():
    curses.start_color()
    curses.use_default_colors()

    Attrs.normal = curses.color_pair(0)

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    Attrs.cur_pos = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    Attrs.cur_col = curses.color_pair(2)

    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    Attrs.cur_row = curses.color_pair(3)

    curses.init_pair(4, curses.COLOR_RED, -1)
    Attrs.error = curses.color_pair(4)

    Attrs.status = Attrs.normal | curses.A_REVERSE
    Attrs.cmd = Attrs.normal | curses.A_REVERSE


#-------------------------------------------------------------------------------

def render_screen(win, vw, mdl):
    x = vw.screen_size.x
    y = vw.screen_size.y - vw.status_size - vw.cmd_size
    
    # Draw the status bar.
    status = vw.status.splitlines()
    assert len(status) == vw.status_size
    for line in status:
        win.addstr(y, 0, pad(line[: x], x), Attrs.status)
        y += 1

    render_output(win, vw)
    render_table(win, vw, mdl)


def render_output(win, vw):
    if vw.error:
        text = vw.error
        attr = Attrs.error
    elif vw.output:
        text = vw.output
        attr = Attrs.normal
    else:
        return

    x = vw.screen_size.x
    y = vw.screen_size.y - vw.cmd_size

    lines = text.splitlines()
    assert len(lines) <= vw.cmd_size
    for line in lines:
        # FIXME: Writing the bottom-right corner causes an error, which is
        # why we use x - 1.
        win.addstr(y, 0, pad(line, x - 1), attr)
        y += 1


def render_table(win, vw, mdl):
    """
    Renders `mdl` with view `vw` in curses `win`.
    """
    # Rebuild the layout.
    vw.layout = view.Layout(mdl, vw)

    # Row numbers to draw.  
    num_rows = mdl.num_rows - vw.scr.y
    max_rows = vw.size.y - 1 if vw.show_header else vw.size.y
    num_rows = min(max_rows, num_rows)
    rows = np.arange(num_rows) + vw.scr.y
    if vw.show_header:
        rows = np.concatenate([[-1], rows])

    # The padding at the left and right of each field value.
    pad = " " * vw.pad

    # Now, draw.
    col_layout = view.shift_layout_cols(vw.layout.cols, vw.scr.x, vw.size.x)
    for x, w, type, z in col_layout:
        c, r = vw.cur

        # The item may be only partially visible.  Compute the start and stop
        # slice bounds to trim it to the screen.
        if x < 0:
            t0 = -x
            x = 0
        else:
            t0 = None
        if x + w >= vw.size.x:
            t1 = vw.size.x - x
        else:
            t1 = None

        if type == "text":
            # A fixed text item.
            text = z[t0 : t1]
            if len(z) > 0:
                for y, row in enumerate(rows):
                    attr =  Attrs.cur_row if row == r else Attrs.normal
                    win.addstr(y, x, text, attr)

        elif type == "col":
            # A column from the model.
            c = z
            fmt = vw.cols[c].fmt
            arr = mdl.get_col(c).arr

            for y, row in enumerate(rows):
                attr = (
                         Attrs.cur_pos if c == vw.cur.c and row == vw.cur.r
                    else Attrs.cur_col if c == vw.cur.c
                    else Attrs.cur_row if                   row == vw.cur.r
                    else Attrs.normal
                )
                if row == -1:
                    # Header.
                    text = palide(mdl.get_col(c).name, w, elide_pos=0.7)
                    attr |= curses.A_UNDERLINE
                else:
                    text = (pad + fmt(arr[row]) + pad)
                win.addstr(y, x, text[t0 : t1], attr)

        elif type == "row_num":
            fmt_str = "0{}d".format(z)
            for y, row in enumerate(rows):
                attr = Attrs.cur_row if row == vw.cur.r else Attrs.normal
                if row == -1:
                    # Header
                    pass
                else:
                    win.addstr(y, x, pad + format(row, fmt_str) + pad, attr)

        else:
            raise NotImplementedError("type: {!r}".format(type))


#-------------------------------------------------------------------------------

class InputAbort(Exception):

    pass



def cmd_input(vw, win, prompt=""):
    """
    Prompts for and reads a line of input in the cmd line.

    @return
      The input text.
    @raise InputAbort
      User cancelled the edit with C-c or C-g.
    """
    def translate(c):
        if c in {3, 7}:  # C-g
            raise InputAbort()
        else:
            return {
                127: curses.KEY_BACKSPACE,
            }.get(c, c)

    # Draw the prompt.
    y = vw.screen_size.y - vw.cmd_size
    win.addstr(y, 0, prompt)
    win.refresh()
    # Create a text input in the rest of the cmd line.
    win = curses.newwin(1, vw.screen_size.x - len(prompt), y, len(prompt))
    box = curses.textpad.Textbox(win)
    curses.curs_set(True)
    # Run it.
    try:
        result = box.edit(translate)
    finally:
        curses.curs_set(False)
    # Not sure why, but edit() always leaves a space at the end.
    if len(result) > 0:
        assert result[-1] == " "
        return result[: -1]
    else:
        return result


#-------------------------------------------------------------------------------

def next_cmd(vw, win, key_map):
    """
    Waits for, then processes the next UI event according to key_map.

    Handles multi-character key combos; collects prefix keys until either
    a complete combo is processed or an input error occurs.

    @raise KeyboardInterrupt
      The program should terminate.
    """
    # Accumulate prefix keys.
    prefix = ()

    # Loop until we have a complete combo.
    while True:
        # Show the combo prefix so far.
        vw.output = " ".join(prefix) + " ..." if len(prefix) > 0 else None

        # Wait for the next UI event.
        render_output(win, vw)
        key, arg = get_key(win)
        logging.debug("key: {!r} {!r}".format(key, arg))
        vw.output = vw.error = None

        # Handle special UI events.
        if key == "RESIZE":
            vw.set_size(arg[0], arg[1])
            return None
        elif key == "LEFTCLICK": 
            view.move_cur_to_coord(vw, arg[0], arg[1])
            return None

        combo = prefix + (key, )
        try:
            cmd_name = key_map[combo]

        except KeyError:
            # Unknown combo.
            logging.debug("unknown combo: {}".format(" ".join(combo)))
            curses.beep()
            # Start over.
            prefix = ()
            continue

        else:
            if cmd_name is keymap.PREFIX:
                # It's a prefix.
                prefix = combo
                continue
            else:
                logging.debug(
                    "combo: {} -> {}".format(" ".join(combo), cmd_name))
                return cmd_name


def main_loop(ctl, vw):
    mdl = ctl.mdl
    key_map = keymap.get_default()

    cmd_args = {
        "ctl"   : ctl,
        "mdl"   : ctl.mdl, 
        "vw"    : vw, 
    }

    with log.replay(), curses_screen() as win:
        sy, sx = win.getmaxyx()
        vw.set_size(sx, sy)

        input = partial(cmd_input, vw, win)

        while True:
            # Construct the status bar contents.
            sl, sr = view.get_status(vw, mdl)
            extra = vw.size.x - len(sl) - len(sr)
            if extra >= 0:
                vw.status = sl + " " * extra + sr
            else:
                vw.status = sl[: extra] + sr

            # Render the screen.
            win.erase()
            render_screen(win, vw, mdl)
            # Process the next UI event.
            try:
                cmd_name = next_cmd(vw, win, key_map)
            except KeyboardInterrupt:
                break

            if cmd_name is None:
                # No command, but we still need to redraw.
                continue

            if cmd_name == "command":
                # Special case: prompt for the command first.
                try:
                    cmd_name = input("command: ")
                except InputAbort:
                    # User aborted.
                    continue

            try:
                result = run(cmd_name, cmd_args, input)
            except InputAbort:
                # User aborted.
                continue
            except CmdError as exc:
                vw.error = "error: {}".format(exc)
                curses.beep()
            else:
                logging.info("command result: {}".format(result))
                if result.msg is not None:
                    logging.info("command message: {}".format(result.msg))
                    vw.output = result.msg


def main():
    logging.basicConfig(filename="log", level=logging.DEBUG)

    mdl = io.load_test(sys.argv[1])
    vw = view.View(mdl)
    ctl = controller.Controller(mdl)

    main_loop(ctl, vw)


if __name__ == "__main__":
    main()


