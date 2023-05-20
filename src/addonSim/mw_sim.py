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
        self.storeRnd()

        self.links = initial_links

        self.entry    : Link           = None
        self.current  : Link           = None
        self.stepsLog : list[Link.key] = None


    def storeRnd(self):
        self.rndState = rnd.getstate()
    def restoreRnd(self, addState=0):
        """ NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple """
        rnd.setstate(self.rndState)
        for i in range(addState): rnd.random()

    #-------------------------------------------------------------------

    def setAll(self, life= 1.0):
        # iterate the global map
        for key,l in self.links.link_map.items():
            l.reset(life)

    def stepAll(self, deg = 0.01):
        # iterate the global map
        for key,l in self.links.link_map.items():
            l.degrade(deg)

    #-------------------------------------------------------------------

    def step(self, deg = 0.01, subSteps = 10):
        # WIP:: flatten per wall self.links -> maybe additional map with separate stuff
        entryKeys = [ id
                    for ids_perWall in self.links.keys_perWall.values() if ids_perWall
                    for id in ids_perWall ]

        if not entryKeys:
            DEV.log_msg(f"Found no entry self.links!", {"SIM", "ERROR"})
            return

        # get input link
        rootLink = self.get_entryLink(entryKeys)
        currentLink = self.get_nextLink(rootLink)
        #DEV.log_msg(f"Root link {rootLink.key_cells} from {len(entryKeys)} -> first {currentLink.key_cells} from {len(rootLink.neighs)}", {"SIM", "STEP"})

        # WIP:: sort input axis aligned to achieve entering by the top of "hill" model
        # WIP:: dict with each iteration info for rendering / study etc

        for i in range(subSteps):
            currentLink.degrade(deg)
            #DEV.log_msg(f"link {currentLink.key_cells} deg to {currentLink.life}", {"SIM", "STEP"})

            # IDEA:: break condition
            if False: break

            # choose link to propagate
            currentLink = self.get_nextLink(currentLink)

    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self, entryKeys:list[Link.key_t]) -> Link:
        weights = [ self.get_entryWeight(lk) for lk in entryKeys ]
        rootKey = rnd.choices(entryKeys, weights)[0]
        #rootKey = rnd.choice(entryKeys)
        return self.links.link_map[rootKey]

    def get_entryWeight(self, linkKey):
        l = self.links.link_map[linkKey]
        w = 0
        w += max(l.pos.y * 10, 0)
        #w += abs(l.pos.z) * 100
        #if l.pos != 0: w = 0
        if abs(l.dir.z) > 0.2: w = 0
        return w


    def get_nextLink(self, currentLink:Link) -> Link:
        weights = [ self.get_nextWeight(lk) for lk in currentLink.neighs ]
        linkKey = rnd.choices(currentLink.neighs, weights)[0]
        #linkKey = rnd.choice(currentLink.neighs)
        return self.links.link_map[linkKey]

    def get_nextWeight(self, linkKey):
        l = self.links.link_map[linkKey]
        w = 1 if not l.toWall else 0
        #if l.life != 1: w = 0
        return max(0, w)