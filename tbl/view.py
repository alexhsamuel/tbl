import dataclasses
import logging
import numpy as np

from   .commands import command, CmdError, CmdResult
from   .formatter import choose_formatter
from   .lib import clip, if_none

#-------------------------------------------------------------------------------

Position    = dataclasses.make_dataclass("Position", ("c", "r"))
Coordinates = dataclasses.make_dataclass("Coordinates", ("x", "y"))

#-------------------------------------------------------------------------------

CFG = {
    "row_num_sep"   : "\u2551",
    "left_border"   : "",
    "separator"     : "\u2502",
    "right_border"  : "\u2551",
    "pad"           : 1,
}

class View:
    """
    Owns the followin state:

    - The order and visibility of columns in the display.
    - Each displayed column's formatter (but not name or contents).
    - The display size of the table.
    - The scroll state of the table in the display.
    - The cursor position.
    - Selection.

    """

    class Col:

        def __init__(self, col_id, fmt):
            self.col_id     = col_id
            self.fmt        = fmt
            self.visible    = True



    def __init__(self, cfg=CFG):
        # Overall dimensions.
        self.screen_size = Coordinates(80, 25)

        # FIXME: Move to controller:
        # Height of status bar.
        self.status_size = 1
        # Status bar text.
        self.status = "?" * 16
        # Height of cmd region.
        self.cmd_size = 1
        # Output or error text in cmd region.
        self.error = None
        self.output = None

        # (x, y) coordinates of the upper-left visible 
        self.scr = Coordinates(0, 0)
        # (c, r) coordinates of the cursor position.
        self.cur = Position(0, 0)

        self.show_header = True
        self.show_row_num = True

        self.cfg = cfg

        # FIXME: Determine this properly.
        row_num_fmt         = lambda n: format(n, "06d")
        row_num_fmt.width   = 6
        self.row_num_fmt    = row_num_fmt

        self.cols           = []
        self.layout         = None


    def add_column(self, col_id, fmt, position=None):
        if position is None:
            position = len(self.cols)
        self.cols.insert(position, self.Col(col_id, fmt))
        return position


    def set_screen_size(self, sx, sy):
        self.screen_size.x = sx
        self.screen_size.y = sy


    @property
    def size(self):
        return Coordinates(
            self.screen_size.x,
            self.screen_size.y - self.status_size - self.cmd_size
        )



def build_view(mdl):
    """
    Builds a view for a model, including all columns.
    """
    vw = View()
    for col in mdl.cols:
        fmt = choose_formatter(col.arr)
        vw.add_column(col.id, fmt)
    return vw


#-------------------------------------------------------------------------------
# Layout

class Layout:
    """
    The transformation between positions and coordinates.

    Lays out (c, r) positions into (x, y) coordinates.  

    - Not aware of scroll state or screen size; computes the layout for the
      entire virtual table relative to (0, 0) upper-left coordinates.

    - Row numbers aren't included in the layout.
    """

    def __init__(self, vw):
        """
        Computes the column layout.

        The layout is a series of `(x, w, val)` tripes, where 
        - `x` is the starting character position
        - `w` is the width
        - `val` is a string literal or a column position
        """
        self.x = 0

        # First, add fixed stuff.
        self.fixed_cols = []
        self.fixed_text = []

        if vw.show_row_num:
            w = vw.row_num_fmt.width + 2 * vw.cfg["pad"]
            self.fixed_cols.append((self.x, w, "row_num"))
            self.x += w
            row_num_sep = vw.cfg["row_num_sep"]
            if row_num_sep:
                w = len(row_num_sep)
                self.fixed_text.append((self.x, w, row_num_sep))
                self.x += w

        # Record where the fixed stuff ends.
        self.fixed_x = self.x

        # Now add scrolling stuff.
        self.cols = []  # (x, width, c)
        self.text = []  # (x, width, text)

        def add_col(w, c):
            self.cols.append((self.x, w, c))
            self.x += w

        def add_text(t):
            w = len(t)
            if w > 0:
                self.text.append((self.x, w, t))
                self.x += w

        need_sep = False

        if vw.cfg["left_border"]:
            add_text(vw.cfg["left_border"])

        for c, col in enumerate(vw.cols):
            if not col.visible:
                continue
            if vw.cfg["separator"] and need_sep:
                add_text(vw.cfg["separator"])
            add_col(col.fmt.width + 2 * vw.cfg["pad"], c)
            need_sep = True
            
        if vw.cfg["right_border"]:
            add_text(vw.cfg["right_border"])


    def locate_col(self, x0):
        """
        Returns the layout entry containing an x coordinate.
        """
        for x, w, c in self.cols:
            if x <= x0 < x + w:
                return c
        else:
            raise LookupError("no col at x: {}".format(x0))


    def get_col(self, c):
        """
        Returns the layout entry for a column.

        :return:
          The x position and width for the column in the layout.
        """
        for x, w, c_ in self.cols:
            if c_ == c:
                return x, w
        else:
            raise LookupError("col not in layout: {}".format(c))



def _rendered_cols(vw, mdl):
    """
    Helper function to set up columns for rendering.
    """
    for x, w, c in vw.layout.fixed_cols:
        if c == "row_num":
            # Row number.
            fmt = vw.row_num_fmt
            arr = np.arange(mdl.num_rows)  # FIXME
            name = "row #"
        else:
            fmt = vw.cols[c].fmt
            col = mdl.get_col(c)
            arr = col.arr
            name = col.name

        yield c, x, w, slice(None, None), name, fmt, arr

    for x, w, c in vw.layout.cols:
        # Shift for scroll position.
        x0 = x - vw.scr.x
        x1 = x0 + w

        if x1 <= vw.layout.fixed_x:
            # Off the left edge.
            continue
        elif vw.size.x <= x0:
            # Off the right edge.
            continue

        # The item may be only partially visible.  Compute a slice to trim
        # it to the visible region.
        s0 = vw.layout.fixed_x - x0
        x0 = max(x0, vw.layout.fixed_x)
        s1 = vw.size.x - x0
        trim = slice(s0 if s0 > 0 else None, s1 if s1 < w else None)

        col     = mdl.get_col(c)
        name    = col.name
        fmt     = vw.cols[c].fmt
        arr     = col.arr

        yield c, x0, w, trim, name, fmt, arr


def _rendered_text(vw, mdl):
    """
    Helper function to set up text decorations for rendering.
    """
    yield from vw.layout.fixed_text

    for x, w, text in vw.layout.text:
        # Shift for scroll position.
        x0 = x - vw.scr.x
        x1 = x0 + w

        if x1 <= vw.layout.fixed_x:
            # Off the left edge.
            continue
        elif vw.size.x <= x0:
            # Off the right edge.
            continue

        # The text may be only partially visible; trim it.
        s0 = vw.layout.fixed_x - x0
        x0 = max(x0, 0)
        s1 = vw.size.x - x0
        text = text[s0 if s0 > 0 else None : s1 if s1 < w else None]

        if len(text) > 0:
            yield x0, w, text


#-------------------------------------------------------------------------------

def get_status(vw, mdl):
    """
    Writes the status bar text.

    @return
      The left- and right-justified portions of the text.
    """
    col     = mdl.cols[vw.cur.c]
    row_num = vw.cur.r
    val     = col.arr[vw.cur.r]
    dtype   = col.arr.dtype

    hidden = sum( not c.visible for c in vw.cols )
    hidden = " [{} cols hidden]".format(hidden) if hidden > 0 else ""

    return (
        "{} [{}]".format(val, dtype) + hidden,
        "{} {:6d}".format(col.name, row_num)
    )


#-------------------------------------------------------------------------------
# Actions

def scroll_to(vw, x=None, y=None):
    """
    Scrolls the vw to a scroll position.
    """
    vw.scr.x = clip(0, if_none(x, vw.scr.x), vw.size.x - 1)
    vw.scr.y = clip(0, if_none(y, vw.scr.y), vw.size.y - 1)


def scroll_to_col(vw, c):
    """
    Scrolls the view such that col `c` is visible.
    """
    # Find the col in the layout.
    x, w = vw.layout.get_col(c)

    # Scroll right if necessary.
    xr = x + w - vw.size.x
    if xr > vw.scr.x:
        logging.info("scroll right: {}".format(xr))
        vw.scr.x = xr

    # Scroll left if necessary.
    xl = x - vw.layout.fixed_x
    if xl < vw.scr.x:
        logging.info("scroll left: {}".format(xl))
        vw.scr.x = xl


def scroll_to_row(vw, r):
    # Scroll up if necessary.
    vw.scr.y = min(r, vw.scr.y)
    # Scroll down if necessary.
    sy = vw.size.y - (1 if vw.show_header else 0)
    vw.scr.y = max(r - sy + 1, vw.scr.y)


def move_cur_to(vw, c=None, r=None):
    vw.cur.c = clip(0, if_none(c, vw.cur.c), len(vw.cols) - 1)
    assert vw.cols[vw.cur.c].visible
    vw.cur.r = clip(0, if_none(r, vw.cur.r), vw.layout.num_rows - 1)
    scroll_to_col(vw, vw.cur.c)
    scroll_to_row(vw, vw.cur.r)


def move_cur_to_coord(vw, x, y):
    """
    Moves the cursor to the position matching coordinates `x, y`.

    Does nothing if the coordinates don't correspond to a position, _e.g._
    the position is on a column separator.
    """
    try:
        c = vw.layout.locate_col(vw.scr.x + x)
    except LookupError:
        pass
    else:
        # FIXME: Compute row number correctly.
        r = vw.scr.y + y - 1
        move_cur_to(vw, c, r)

    
def _next_visible(cols, c):
    return next( c for c in range(c + 1, len(cols)) if cols[c].visible )
        

def _prev_visible(cols, c):
    return next( c for c in range(c - 1, -1, -1) if cols[c].visible )

             
def hide_col(vw, c):
    if vw.cols[c].visible:
        vw.cols[c].visible = False
    else:
        raise CmdError("column already hidden")

    # If we hide a column to the left of the current col, move to the left.
    if vw.cur.c == c:
        try:
            vw.cur.c = _next_visible(vw.cols, c)
        except StopIteration:
            vw.cur.c = _prev_visible(vw.cols, c)
        # FIXME: What if we hide the last column?


#-------------------------------------------------------------------------------
# Commands

@command()
def move_left(vw):
    try:
        c = _prev_visible(vw.cols, vw.cur.c)
    except StopIteration:
        pass
    else:
        move_cur_to(vw, c=c)


@command()
def move_right(vw):
    try:
        c = _next_visible(vw.cols, vw.cur.c)
    except StopIteration:
        pass
    else:
        move_cur_to(vw, c=c)


@command()
def move_up(vw):
    move_cur_to(vw, r=vw.cur.r - 1)


@command()
def move_down(vw):
    move_cur_to(vw, r=vw.cur.r + 1)


@command()
def move_up_page(vw):
    move_cur_to(vw, r=vw.cur.r - (vw.size.y - 2))


@command()
def move_down_page(vw):
    move_cur_to(vw, r=vw.cur.r + (vw.size.y - 2))


@command()
def scroll_left(vw):
    scroll_to(vw, vw.scr.x - 1)


@command()
def scroll_right(vw):
    scroll_to(vw, vw.scr.x + 1)


@command()
def toggle_show_row_num(vw):
    vw.show_row_num = not vw.show_row_num


@command()
def hide_column_name(vw, mdl, name):
    try:
        col, = ( c for c in mdl.cols if c.name == name )
    except ValueError:
        raise CmdError("no column: {}".format(name))
    hide_col(vw, col.id)
    return CmdResult(msg="column hidden: {}".format(name))


@command()
def hide_column(vw, mdl):
    c = vw.cur.c
    hide_col(vw, c)
    col = mdl.get_col(c)
    return CmdResult(msg="column hidden: {}".format(col.name))


