# coding: utf-8
# h5tools: convenience functions for dealing with hdf5 and nexus files
# author: Sofya Laskina, Brian R. Pauw, I. Bressler
# date: 2022.01.10

import h5py
import logging
import numpy as np


def h5Get(filename, h5path, default="none", leaveAsArray=False):
    """ get a single value from an HDF5 file, with added error checking and default handling"""
    with h5py.File(filename, "r") as h5f:
        try:
            val = h5f.get(h5path)[()]
            val = h5py_casting(val)  # sofya added this line
            # logging.info('type val {} at key {}: {}'.format(val, h5path, type(val)))

        except TypeError:
            logging.warning(
                "cannot get value from file path {}, setting to default".format(h5path)
            )
            val = default
    return val


def h5GetDict(filename, keyPaths):
    """creates a dictionary with results extracted from an HDF5 file"""
    resultDict = {}
    for key, h5path in keyPaths.items():
        resultDict[key] = h5Get(
            filename, key
        )  # this probably needs to be key, not h5path
    return resultDict


def h5py_casting(val, leaveAsArray=False):
    if isinstance(val, np.ndarray) and (not leaveAsArray):
        if val.size == 1:
            val = np.array([val.squeeze()])[0]
        else:
            if np.isnan(val).sum() + np.isinf(val).sum() == np.prod(
                [i for i in val.shape]
            ):
                # print('all elements are either nan or inf')
                val = "-"
            elif np.isnan(val.mean()) or np.isinf(val.mean()):
                # print('nan pixel at index', np.argwhere(np.isnan(val)))
                # print('inf pixel at index', np.argwhere(np.isinf(val)))
                val = np.mean(np.ma.masked_invalid(val))
            else:
                val = val.mean()
    """if isinstance( val, np.ndarray) and leaveAsArray: seems to take a lot of time
        val = val.tolist()
        return json.dumps(val, separators=(',', ':'), sort_keys=True, indent=4)"""
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        val = "-"
    if isinstance(val, np.bytes_) or isinstance(val, bytes):
        val = val.decode("UTF-8")
    if isinstance(val, np.generic):
        val = val.item()
    if isinstance(val, str):
        if val[:2] == "b'":
            val = val[2:-1]
    return val
