# %% import the library
print("\n-----------------------------------------------------------------------------------------")
from tess import Container, Cell

# %% check out the API
from pprint import pprint
from inspect import getmembers, ismethod
from types import FunctionType

def attributes(obj):
    disallowed_names = {
      name for name, value in getmembers(type(obj))
        if isinstance(value, FunctionType)}
    return {
      name: getattr(obj, name) for name in dir(obj)
        if name[0] != '_' and name not in disallowed_names and hasattr(obj, name)}

def print_attributes(obj):
    pprint(attributes(obj), indent=2)

print("print_attributes(Container)")
print_attributes(Container)
print("print_attributes(Cell)")
print_attributes(Cell)

# %% Calling all methods for testing
cont = Container([[1,1,1]], limits=(2,2,2), periodic=False)
cell = cont[0]

for a,m in attributes(Cell).items():
    call = callable(m)
    data = m(cell) if call else getattr(cell, a)
    print('{0:20} {1} {2}'.format(a, data, "(attr)" if not call else ""))


# %% Using a container
# cont = Container([[1,1,1], [2,2,2]], limits=(3,3,3), periodic=False)
cont = Container([[1,1,1]], limits=(2,2,2), periodic=False)

print("pos", [v.pos for v in cont])
print("centroid", [v.centroid() for v in cont])
print("neighbors", [v.neighbors() for v in cont])
# print("normals", [v.normals() for v in cont])
print("face_areas", [v.face_areas() for v in cont])
