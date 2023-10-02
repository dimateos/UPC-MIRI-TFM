from math import sin,cos
from .preferences import getPrefs
# HACK:: simple way to avoid circular import
#from .properties import MW_resistance_cfg

# OPT:: edit from UI or plot in notebook?
#-------------------------------------------------------------------

def user_in_cfg(x,y):
    #cfg : MW_resistance_cfg = getPrefs().resist_cfg
    cfg = getPrefs().resist_cfg
    if cfg.in_flipX: x *= -1
    if cfg.in_flipY: y *= -1
    return x,y

def user_out_cfg(r):
    #cfg : MW_resistance_cfg = getPrefs().resist_cfg
    cfg = getPrefs().resist_cfg
    if cfg.out_inv: r = 1-r
    if cfg.out_round: r = round(r)
    return r

class LAYERS_SIDE:
    def get2D(x, y):
        x,y = user_in_cfg(x,y)
        r = sin(-1 * x + 0.5 * y)
        r = (0.5 * r + 0.5) # normalize
        return user_out_cfg(r)

class LAYERS_STACK:
    def get2D(x, y):
        x,y = user_in_cfg(x,y)
        r = sin(1 * y + -0.3 * x)
        r = (0.5 * r + 0.5) # normalize
        return user_out_cfg(r)

class POCKETS:
    def get2D(x, y):
        x,y = user_in_cfg(x,y)
        r = sin(x) + cos(y)
        r = (r+2.0) / 4.0 # normalize
        return user_out_cfg(r)

# field selector
_fields_map = {
    "LAYERS_SIDE": LAYERS_SIDE,
    "LAYERS_STACK": LAYERS_STACK,
    "POCKETS": POCKETS,
}
_field_R_current = LAYERS_SIDE

def field_R_current_switch(field_cfg):
    global _field_R_current, _fields_map
    names = field_cfg.copy()
    field_name = names.pop()
    _field_R_current = _fields_map[field_name]

def field_R_current():
    global _field_R_current
    return _field_R_current