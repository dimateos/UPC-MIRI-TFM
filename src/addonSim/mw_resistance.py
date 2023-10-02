from math import sin,cos
from .preferences import getPrefs
from .properties import MW_resistance_cfg

# OPT:: edit from UI or plot in notebook?
#-------------------------------------------------------------------


def user_in_cfg(x,y):
    cfg : MW_resistance_cfg = getPrefs().resist_cfg
    if cfg.in_flipX: x *= -1
    if cfg.in_flipY: y *= -1
    return x,y

def user_out_cfg(r):
    cfg : MW_resistance_cfg = getPrefs().resist_cfg
    if cfg.out_inv: r = 1-r
    if cfg.out_round: r = round(r)
    return r

class LAYERS_SIDE:
    def get2D(x, y):
        x,y = user_in_cfg(x,y)
        r = sin(-1 * x + 0.5 * y)
        r = (0.5 * r + 0.5) # normalize
        return user_out_cfg(r)

class POCKETS:
    def get2D(x, y):
        x,y = user_in_cfg(x,y)
        r = sin(x) + cos(y)
        r = (r+2.0) / 4.0 # normalize
        return user_out_cfg(r)

MW_field_R = LAYERS_SIDE

MW_fields = {
    "LAYERS_SIDE": LAYERS_SIDE,
    #"LAYERS_SIDE": LAYERS_SIDE,
    "POCKETS": POCKETS,
}