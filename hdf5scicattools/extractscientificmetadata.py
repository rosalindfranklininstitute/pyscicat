# coding: utf-8
# sciMeta: extract all metadata from a NeXus file and put it in a tree for upload as scientific metadata to SciCat
# author: Sofya Laskina, Brian R. Pauw
# date: 2022.01.10

import h5py
import hdf5plugin # ESRF's library that extends the read functionality of HDF5 files, adding a couple of compression filters
from .h5tools import h5py_casting
import logging
from collections import abc

def update_deep(dictionary, path_update):
    """
    Update the main metadata dictionary with the new dictionary.
    """
    k = list(path_update.keys())[0]
    v = list(path_update.values())[0]
    if k not in dictionary.keys():
        dictionary[k] = v
    else:
        key_next = list(path_update[k].keys())[0] 
        if key_next in dictionary[k].keys():
            dictionary[k] = update_deep(dictionary.get(k, {}), v)
        else:
            dictionary[k].update(v)
    return dictionary

def build_dictionary( levels, update_data):
    """"
    Creates a json-like level based dictionary for the whole path starting from /entry1 or whatever the first child of the root in the datatree is.
    """
    for level in levels[::-1]:
        update_data = dict({level:update_data})
    return update_data


def unwind(h5f, parent_path, metadata, default = 'none', leaveAsArray = False):
    """
    Current_level is the operating level, that is one level higher that the collected data.
    """
    if isinstance(h5f.get(parent_path), abc.Mapping):
        new_keys = h5f.get(parent_path).keys()
        for nk in sorted(new_keys):
            unwind(h5f, '/'.join([parent_path, nk]), metadata)
    else:
        try:
            val = h5f.get(parent_path)[()]
            val = h5py_casting(val,leaveAsArray)
        except (OSError, TypeError) as e:
            logging.warning(f"file has no value at path {parent_path}, setting to default: {default}")
            val = default

        attributes = {'value':val}
        try:
            attributes_add = h5f.get(parent_path).attrs
            a_key = attributes_add.keys()
            a_value = []
            for v in attributes_add.values():
                v = h5py_casting(v,leaveAsArray)
                a_value.append(v)
            attributes.update(dict(zip(a_key, a_value)))
        except (KeyError, AttributeError) as e:
            logging.warning(e)
            
        levels = parent_path.split('/')[1:]
        if list(attributes.keys()) == ['value']:# no attributes here
            nested_dict = val
        else:
            nested_dict = attributes.copy()
        if val != '':
            update_dict = build_dictionary(levels,nested_dict)
            metadata = update_deep(metadata, update_dict)

def extractScientificMetadata(filename, excludeRootEntryList:list = ['Saxslab'], includeRootEntry:bool=False):
    """
    Goals:
    --
    Opens an HDF5 or nexus file and unwinds the structure to add up all the metadata and respective attributes. 
    This adds the paths and structure as required for SciCat's "scientific metadata" upload. 

    Usage:
    --
    Root branches to omit can be listed using the argument "excludeList". Example:
    scientificMetadata=extractScientificMetadata(Path('./my_file.h5'), excludeList=['Saxslab']) 
    The example will only read the /entry, and not the /Saxslab tree. 

    Limitations:
    --
    For Reasons, the exclude root entry list will be ignored if you include the root entry/entries.
    """
    with h5py.File(filename, "r") as h5f:
        prior_keys = list(h5f.keys())
        [prior_keys.remove(removeKey) for removeKey in excludeRootEntryList if removeKey in prior_keys]
        metadata = dict() #.fromkeys(prior_keys)
        
        # walk through the tree and deposit entries into the dict. 
        if includeRootEntry: 
            unwind(h5f, '/', metadata) # todo: this does not skip unwanted entries
        else: # walk through the list of prior keys 
            for pk in sorted(prior_keys):
                unwind(h5f, '/' + str(pk), metadata)            

        if len(metadata.keys())==1:
            return metadata[list(metadata.keys())[0]]
        else:
            return metadata
