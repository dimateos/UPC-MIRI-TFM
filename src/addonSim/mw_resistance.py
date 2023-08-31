from mathutils import Vector
from math import sin


#-------------------------------------------------------------------

def _step_function(value):
    return 1 if value >= 0 else -1

def _step_function_1_0(value):
    return 1 if value >= 0 else 0

def get2D(x, y):
    r = 0.5 * sin((3 * y)) + 0.5
    #r = 0.5 * sin((5 * x + 3 * y)) + 0.5
    step = _step_function(sin(20 * y) + 0.8)
    return r

# TODO:: maybe just get color from R
def get2D_color4D(x, y):
    r = get2D(x,y)
    if r >= 0:
        return Vector([r,0,0,1])
    else:
        return Vector([0,0,-r,1])
