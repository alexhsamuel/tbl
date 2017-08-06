"""
Mapping from key combos to commands

A key map is a mapping from keys or key combos to commands.  The keys may
be single key codes, or sequence of key codes for key combos.  The values
are commands.  A value of `PREFIX` indicates a prefix key; each prefix of a 
a key combo must be tagged as a prefix in this way.
"""

#-------------------------------------------------------------------------------

from   functools import partial

from   . import commands, controller, io, model, view
from   . import screen as scr

#-------------------------------------------------------------------------------

PREFIX = object()

def check_key_map(key_map):
    # Convert single character keys to tuples, for convenience.
    key_map = {
        (k, ) if isinstance(k, str) else tuple( str(s) for s in k ): v
        for k, v in key_map.items()
    }

    # Check prefixes.
    for combo in [ k for k in key_map if len(k) > 1 ]:
        prefix = combo[: -1]
        while len(prefix) > 1:
            if key_map.setdefault(prefix, None) is not PREFIX:
                raise ValueError(
                    "combo {} but not prefix {}".format(combo, prefix))
            prefix = prefix[: -1]
            
    return key_map


def get_default():
    """
    Returns the default key map.
    """
    return check_key_map({
        "LEFT"          : partial(view.cmd_move_cur, dc=-1),
        "RIGHT"         : partial(view.cmd_move_cur, dc=+1),
        "UP"            : partial(view.cmd_move_cur, dr=-1),
        "DOWN"          : partial(view.cmd_move_cur, dr=+1),
        "LEFTCLICK"     : view.cmd_move_cur_to,
        "S-LEFT"        : partial(view.cmd_scroll, dx=-1),
        "S-RIGHT"       : partial(view.cmd_scroll, dx=+1),
        "M-#"           : view.cmd_toggle_show_row_num,
        "C-k"           : controller.cmd_delete_row,
        "C-x"           : PREFIX,
        ("C-x", "C-s")  : io.cmd_save,
        ("C-x", "C-w")  : io.cmd_save_as,
        "C-z"           : controller.cmd_undo,
        "q"             : commands.cmd_quit,
        "RESIZE"        : lambda screen, arg: scr.set_size(screen, arg[0], arg[1]),
    })


