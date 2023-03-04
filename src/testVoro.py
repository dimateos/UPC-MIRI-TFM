
# %% Checking out an API
from pprint import pprint
from inspect import getmembers, ismethod
from types import FunctionType

def get_attributes(obj, queryDoc = False, queryCall = False):
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
                data = attr() if queryCall else attr
                callables[name] = data
            else:
                data = attr
                properties[name] = data

        except:
            continue

    return callables, properties, docs

def print_attributes(obj,  queryDoc = False, queryCall = False):
    calls, props, docs = get_attributes(obj, queryDoc, queryCall)
    if queryDoc: print("> doc:", obj.__doc__)

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

# %% Library class API
print("\n-----------------------------------------------------------------------------------------")
from tess import Container, Cell

print("\n? print_attributes(Container)")
print_attributes(Container, True)
print("\n? print_attributes(Cell)")
print_attributes(Cell, True)

# %% Calling all methods on an instance
# cont = Container([[1,1,1]], limits=(2,2,2), periodic=False)

l = 0.5
c = [0,0,0]
bb = [ [cc-l for cc in c], [cc+l for cc in c] ]
cont = Container(points=[(0,0,0)], limits=bb)

print("\n? print_attributes(cont[0])", cont)
print_attributes(cont[0], False, True)

# %% Using a container
cont = Container([(1,1,1), (2,2,2)], limits=(3,3,3), periodic=False)

print("\n? aggregated cells data", cont)
print('- {0:20} {1}'.format("pos", [c.pos for c in cont]))
print('- {0:20} {1}'.format("centroid", [c.centroid() for c in cont]))
print('- {0:20} {1}'.format("neighbors", [c.neighbors() for c in cont]))
# print('- {0:20} {1}'.format("normals", [c.normals() for c in cont]))
# print('- {0:20} {1}'.format("face_areas", [c.face_areas() for c in cont]))

