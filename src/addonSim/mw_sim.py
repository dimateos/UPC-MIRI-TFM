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
# WIP:: atm just a static method -> should be a class with accesss to link collection, initial state, etc

def setAll(links: LinkCollection, life= 1.0):
    # iterate the global map
    for key,l in links.link_map.items():
        l.reset(life)

def stepAll(links: LinkCollection, deg = 0.01):
    # iterate the global map
    for key,l in links.link_map.items():
        l.degrade(deg)

#-------------------------------------------------------------------

def step(links: LinkCollection, deg = 0.01, subSteps = 10):
    # WIP:: flatten per wall links -> maybe additional map with separate stuff
    entryKeys = [ id
                  for ids_perWall in links.keys_perWall.values() if ids_perWall
                  for id in ids_perWall ]

    if not entryKeys:
        DEV.log_msg(f"Found no entry links!", {"SIM", "ERROR"})
        return

    # get input link
    rootLink = get_entryLink(links, entryKeys)
    currentLink = get_nextLink(links, rootLink)
    #DEV.log_msg(f"Root link {rootLink.key_cells} from {len(entryKeys)} -> first {currentLink.key_cells} from {len(rootLink.neighs)}", {"SIM", "STEP"})

    # WIP:: sort input axis aligned to achieve entering by the top of "hill" model
    # WIP:: dict with each iteration info for rendering / study etc

    for i in range(subSteps):
        currentLink.degrade(deg)

        # IDEA:: break condition
        if False: break

        # choose link to propagate
        currentLink = get_nextLink(links, currentLink)

#-------------------------------------------------------------------
#  https://docs.python.org/dev/library/random.html#random.choices

def get_entryLink(links: LinkCollection, entryKeys:list[Link.keyType]) -> Link:
    weights = [ get_entryWeight(links, lk) for lk in entryKeys ]
    rootKey = rnd.choices(entryKeys, weights)[0]
    #rootKey = rnd.choice(entryKeys)
    return links.link_map[rootKey]

def get_entryWeight(links: LinkCollection, linkKey):
    l = links.link_map[linkKey]
    w = 0
    w += max(l.pos.y * 10)
    w += abs(l.pos.z) * 100
    return w

def get_nextLink(links: LinkCollection, currentLink:Link) -> Link:
    weights = [ get_entryWeight(links, lk) for lk in currentLink.neighs ]
    linkKey = rnd.choices(currentLink.neighs, weights)[0]
    #linkKey = rnd.choice(currentLink.neighs)
    return links.link_map[linkKey]

def get_nextWeight(links: LinkCollection, linkKey):
    l = links.link_map[linkKey]
    w = 1 if not l.toWall else 0
    return max(0, w)