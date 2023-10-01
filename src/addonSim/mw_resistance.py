from math import sin,cos
from .utils_dev import DEV

# OPT:: edit from UI or plot in notebook?
#-------------------------------------------------------------------

class LAYERS:
    def get2D(x, y):
        r = sin(-1 * x + 0.5 * y)
        r = (0.5 * r + 0.5) # normalize
        if DEV.FORCE_RESISTANCE_ROUND:
            r = round(r)
        return r

class POCKETS:
    def get2D(x, y):
        r = sin(x) + cos(y)
        r = (r+2.0) / 4.0 # normalize
        if DEV.FORCE_RESISTANCE_ROUND:
            r = round(r)
        return r

MW_field_R = LAYERS