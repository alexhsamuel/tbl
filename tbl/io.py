import csv
import logging
import numpy as np

from   .commands import command, CmdResult, CmdError
from   .model import Model

#-------------------------------------------------------------------------------

def _convert_to_int(arr):
    """
    Tries to convert `arr` to an int array.
    """
    empty = arr == ""
    if empty.all():
        raise ValueError("no non-empty values")
    return 


def _convert_to_float(arr):
    """
    Tries to convert `arr` to a float array, interpreting empty strings as NaN.
    """
    empty = arr == ""
    if empty.all():
        raise ValueError("no non-empty values")

    val         = np.empty(arr.shape, dtype=float)
    val[~empty] = arr[~empty].astype(float)
    val[ empty] = np.nan
    return val


def guess_convert(arr):
    """
    Attempt to convert `arr` to "more specific" types.
    """
    arr = np.asarray(arr)

    try:
        return arr.astype(int)
    except ValueError:
        pass

    try:
        return _convert_to_float(arr)
    except ValueError:
        pass

    try:
        return arr.astype(bool)
    except ValueError:
        pass

    return arr


def load_test(path):
    with open(path) as file:
        reader = csv.reader(file)
        rows = iter(reader)
        names = next(rows)
        arrs = zip(*list(rows))
    mdl = Model(path)
    for arr, name in zip(arrs, names):
        arr = guess_convert(arr)
        mdl.add_col(arr, name)
    return mdl


def _save(mdl, filename):
    """
    Save the model to a file.
    TODO: This needs a lot of work to preserve
    formatting, etc.
    :param mdl:
    :param filename:
    :param new_filename:
    :return:
    """
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile)
        # write header
        header = [col.name for col in mdl.cols]
        writer.writerow(header)
        # write rows.
        for row_num in range(mdl.num_rows):
            row = [str(c.arr[row_num]) for c in mdl.cols]
            writer.writerow(row)


#-------------------------------------------------------------------------------
# Commands

@command()
def save(mdl):
    # FIXME: Confirm overwrite.
    _save(mdl, mdl.filename)
    return CmdResult(msg="saved: {}".format(mdl.filename))


@command()
def save_as(mdl, filename):
    if len(filename) == 0:
        raise CmdError("empty filename")
    # FIXME: Confirm overwrite.
    _save(mdl, filename)
    mdl.filename = filename
    return CmdResult(msg="saved: {}".format(filename))


