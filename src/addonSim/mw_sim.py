import bpy.types as types
from mathutils import Vector, Matrix
import random as rnd

from .preferences import getPrefs

from .mw_links import LinkCollection, Link
from tess import Container, Cell

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------
# IDEA:: could have a globlal class etc?

class Simulation:

    def __init__(self, initial_links: LinkCollection):
        self.life = 1.0


#-------------------------------------------------------------------
# WIP:: atm just a static method

def setAll(links: LinkCollection, life= 1.0):
    # iterate the global map
    for key,l in links.link_map.items():
        l.life = max(0, life)
        l.life = min(1, life)

def stepAll(links: LinkCollection, deg = 0.01):
    # iterate the global map
    for key,l in links.link_map.items():
        l.life = max(0, l.life-deg)

def step(links: LinkCollection, subSteps = 10, deg = 0.01):
    # get entry links should be calculated
    entryKeys = [ id
                  for ids_perWall in links.keys_perWall.values() if ids_perWall
                  for id in ids_perWall ]

    if not entryKeys:
        DEV.log_msg(f"Found no entry links!", {"SIM", "ERROR"})
        return

    rootKey = rnd.choice(entryKeys)
    rootLink = links.link_map[rootKey]
    #DEV.log_msg(f"Root link {rootKey} from {len(entryKeys)} options", {"SIM", "STEP"})

    return # WIP::