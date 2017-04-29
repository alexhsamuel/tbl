from   __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
import select
import sys
import termios
import tty

#-------------------------------------------------------------------------------

TRANSLATION = {
    b"\x01"     : b"^A",
    b"\x02"     : b"^B",
    b"\x04"     : b"^D",
    b"\x05"     : b"^E",
    b"\x06"     : b"^F",
    b"\x07"     : b"^G",
    b"\x08"     : b"^H",
    b"\x0b"     : b"^K",
    b"\x0c"     : b"^L",
    b"\x0e"     : b"^N",
    b"\x10"     : b"^P",
    b"\x12"     : b"^R",
    b"\x14"     : b"^T",
    b"\x15"     : b"^U",
    b"\x17"     : b"^W",
    b"\x18"     : b"^X",
    b"\x1bOP"   : b"F1",
    b"\x1bOQ"   : b"F2",
    b"\x1bOR"   : b"F3",
    b"\x1bOS"   : b"F4",
    b"\x1b[15~" : b"F5",
    b"\x1b[17~" : b"F6",
    b"\x1b[18~" : b"F7",
    b"\x1b[19~" : b"F8",
    b"\x1b[20~" : b"F9",
    b"\x1b[21~" : b"F10",
}

@contextlib.contextmanager
def raw_keyboard(file):
    # Save old attributes.
    old_attr = termios.tcgetattr(file)

    attr = termios.tcgetattr(file)
    # Disable character echoing and canonical (line) mode.
    attr[3] &= ~(termios.ECHO | termios.ICANON)
    # Disable minimum read size and timer.
    attr[6][termios.VMIN] = 0
    attr[6][termios.VTIME] = 0
    termios.tcsetattr(file, termios.TCSADRAIN, attr)

    try:
        yield
    finally:
        termios.tcsetattr(file, termios.TCSADRAIN, old_attr)



if __name__ == "__main__":
    with raw_keyboard(sys.stdin):
        while True:
            sel = select.select([sys.stdin], [], [], 0)
            if len(sel[0]) > 0:
                key = sys.stdin.read(8)  # FIXME: Is 8 enough?
                if len(key) > 0:
                    print(repr(TRANSLATION.get(key, key)))


