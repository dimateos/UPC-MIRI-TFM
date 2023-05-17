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


_rndState = None
def storeRnd():
    global _rndState
    _rndState = rnd.getstate()
def restoreRnd(addState=0):
    global _rndState
    rnd.setstate(_rndState)

    # NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple
    for i in range(addState): rnd.random()

#-------------------------------------------------------------------
# WIP:: atm just a static method

def setAll(links: LinkCollection, life= 1.0):
    # iterate the global map
    for key,l in links.link_map.items():
        l.reset(life)

def stepAll(links: LinkCollection, deg = 0.01):
    # iterate the global map
    for key,l in links.link_map.items():
        l.degrade(deg)

def step(links: LinkCollection, deg = 0.01, subSteps = 10):
    # get entry links should be calculated
    entryKeys = [ id
                  for ids_perWall in links.keys_perWall.values() if ids_perWall
                  for id in ids_perWall ]

    if not entryKeys:
        DEV.log_msg(f"Found no entry links!", {"SIM", "ERROR"})
        return

    rootKey = rnd.choice(entryKeys)
    rootLink = links.link_map[rootKey]
    linkKey = rnd.choice(rootLink.neighs)
    link = links.link_map[linkKey]
    #DEV.log_msg(f"Root link {rootKey} from {len(entryKeys)} -> first {linkKey} from {len(rootLink.neighs)}", {"SIM", "STEP"})

    # WIP:: sort input axis aligned to achieve entering by the top of "hill" model
    # WIP:: dict with each iteration info for rendering / study etc

    for i in range(subSteps):
        link.degrade(deg)

        # IDEA:: break condition
        if False: break

        # choose link to propagate
        linkKey = rnd.choice(link.neighs)
        link = links.link_map[linkKey]