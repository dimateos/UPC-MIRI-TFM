from mathutils import Vector
from math import sin,cos
import numpy as np

# TODO:: edit from UI or plot in notebook
#-------------------------------------------------------------------

# layers
def get2D(x, y):
    r = sin(-1 * x + 0.5 * y)
    r = (0.5 * r + 0.5) # normalize
    return r

## pockets of resistance
#def get2D(x, y):
#    r = sin(x) + cos(y)
#    r = (r+2.0) / 4.0 # normalize
#    return r