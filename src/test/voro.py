# %% Library class API
from addon.info_inspect import *

print("\n-----------------------------------------------------------------------------------------")
from tess import Container, Cell

print("\n? print_attributes(Container)")
print_attributes(Container, True)
print("\n? print_attributes(Cell)")
print_attributes(Cell, True)

# %% Calling all methods on an instance
# cont = Container([[1,1,1]], limits=(2,2,2), periodic=False)

l = 0.5
c = [1,1,1]
bb = [ [cc-l for cc in c], [cc+l for cc in c] ]
cont = Container(points=[c], limits=bb)

print("\n? print_data(cont[0])", cont)
print_data(cont[0])

# %% Read err ouput?
import py, sys
capture = py.io.StdCaptureFD(out=False, in_=False)
ns = cont[0].neighbors()
sys.stderr.write("world")
out,err = capture.reset()
print("out", out)
print("err", err)

# %% list container methods
print_attributes(Container, False)
print_data(cont, False)
# print(cont.order())
print(cont.get_limits())

# %% transform methods
cont[0].translate(10,10,10)

# %% Aggregating results of the methods
cont = Container([(1,1,1), (2,2,2)], limits=(3,3,3), periodic=False)

print("\n? aggregated cells data", cont)
print_data(cont)
# face_freq_table: number of edges that each face has (as freq table)
# face_orders: number of edges per face (implemented in fork!)


# %% Comparing separated cells

print('- {0:20} {1}'.format("id", [c.id for c in cont]))
print('- {0:20} {1}'.format("pos", [c.pos for c in cont]))
print('- {0:20} {1}'.format("centroid", [c.centroid() for c in cont]))
print('- {0:20} {1}'.format("neighbors", [c.neighbors() for c in cont]))

print("\n? print_data(cont[0])", cont[0])
print_data(cont[0])
print("\n? print_data(cont[1])", cont[1])
print_data(cont[1])

# %% testing intellisense
cell = cont[0]
# cell.
# Pycharm has total autocomplete while vscode lacks the info inside the .pyx file
# NOTE the issue is Pylance https://github.com/microsoft/pylance-release/issues/674

# the alternative Jedi python language server detects the docs, but is not as smart as Pycharms
# it can scrape the documentation from .pyx and autocomplete cell = Cell(), but not infer it from cont[0]
# as a workaround one can annotate the type in the declaration or by dynamically asserting it
# NOTE managed to solve globally by annotating the Container class inheritance pattern, it still cannot go to definition etc
assert isinstance(cell, Cell)
cell: Cell = cont[0]

#cells = [ (c, c.vertices()) for c in cont ]

