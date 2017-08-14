from   collections import OrderedDict as odict
import numpy as np

from   tbl.model import Model
from   tbl.view import View, lay_out_cols

#-------------------------------------------------------------------------------

def test_lay_out_0():
    mdl = Model(filename=None)
    mdl.add_col(np.array([ 1,  2,  3]), "foo")
    mdl.add_col(np.array([ 8,  9, 10]), "bar")
    vw = View(mdl)
    vw.show_row_num  = False
    vw.left_border   = "|>"
    vw.separator     = "||"
    vw.right_border  = "<|"

    assert [ tuple(l) for l in lay_out_cols(mdl, vw) ] == [
        ( 0, 2, "text", "|>"),
        ( 2, 3, "col", 0),
        ( 5, 2, "text", "||"),
        ( 7, 4, "col", 1),
        (11, 2, "text", "<|"),
    ]


