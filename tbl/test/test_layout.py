from   collections import OrderedDict as odict
import numpy as np

from   tbl.screen import Model, State, lay_out_cols

#-------------------------------------------------------------------------------

def test_lay_out_0():
    model = Model([
        Model.Col("foo", np.array([ 1,  2,  3])),
        Model.Col("bar", np.array([ 8,  9, 10])),
    ])
    state = State(model)
    state.left_border   = "|> "
    state.separator     = " || "
    state.right_border  = " <|"

    layout = lay_out_cols(model, state)
    layout = [ tuple(p) for p in layout ]
    assert layout == [
        ( 0, "|> "),
        ( 3, 0),  # col 0
        ( 4, " || "),
        ( 8, 1),  # col 1
        (10, " <|"),
    ]


