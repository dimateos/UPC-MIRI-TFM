
from pprint import pprint
from inspect import getmembers, ismethod
from types import FunctionType


# -------------------------------------------------------------------

def get_attributes(obj, queryDoc = False):
    """ Retrieve the attributes separated by callables and properties
    """
    disallowed_names = {
        name for name, value in getmembers(type(obj))
        if isinstance(value, FunctionType)
    }

    callables = dict()
    properties = dict()
    docs = dict()

    for name in dir(obj):
        # Ignore private methods
        if name[0] == "_" or name in disallowed_names: continue

        # Some names may not be retrievable
        try:
            attr = getattr(obj, name)
            if queryDoc: docs[name] = attr.__doc__

            # Distinguish callable and optionally store the result
            if callable(attr):
                callables[name] = attr
            else:
                properties[name] = attr

        except:
            continue

    return callables, properties, docs

def get_data(obj):
    """ Retrieve the attributes separated by callables (CALLED) and properties
    """
    calls, props, _ = get_attributes(obj)
    for k,v in calls.items():
        try:
            calls[k]= v()
        except:
            calls[k] = "*needs input arguments*"

    return calls, props

def _print_attr(calls, props, docs = None):
    def _print(d):
        for name, val in d.items():
            print('- {0:20} {1}'.format(name, val))
            if docs and docs[name]: print("     ", docs[name])

    if calls:
        print("\n> calls:")
        _print(calls)
    if props:
        print("\n> props:")
        _print(props)

def print_attributes(obj,  queryDoc = False):
    if queryDoc: print("> doc:", obj.__doc__)
    _print_attr(*get_attributes(obj, queryDoc))

def print_data(obj, checkList = True):
    if checkList and isinstance(obj, list):
        calls_props = [ get_data(o) for o in obj ]

        # aggregate the data per key
        calls = dict()
        for k in calls_props[0][0].keys():
            calls[k]= [ c[k] for c,p in calls_props ]

        props = dict()
        for k in calls_props[0][1].keys():
            props[k]= [ p[k] for c,p in calls_props ]

    else:
        calls, props = get_data(obj)

    _print_attr(calls, props)