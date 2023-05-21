import bpy.types as types
from mathutils import Vector, Matrix
import random as rnd

from .preferences import getPrefs

from .mw_links import LinkCollection, Link
from tess import Container, Cell

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------
# IDEA:: toggle full log / etc

class SubStepInfo:
    def __init__(self):
        pass
class StepInfo:
    def __init__(self):
        self.sub : list[SubStepInfo] = list()


class Simulation:
    def __init__(self, links_initial: LinkCollection, deg = 0.05, log = True):
        self.storeRnd()

        self.links = links_initial
        self.initial_life = [ l.life for l in self.links.links_Cell_Cell ]
        self.deg = deg

        self.entry    : Link           = None
        self.current  : Link           = None

        self.log = log
        self.simInfo : list[StepInfo] = list()
        self.stepInfo : StepInfo = None
        self.subInfo : SubStepInfo = None
        self.id_step = self.id_substep = -1

    def set_deg(self, deg):
        self.deg = deg

    def resetSim(self):
        self.restoreRnd()
        for i,l in enumerate(self.links.links_Cell_Cell):
            l.life = self.initial_life[i]

        if self.log:
            self.simInfo.clear()
            self.stepInfo : StepInfo = None
            self.subInfo : SubStepInfo = None
        self.id_step = self.id_substep = -1

    def storeRnd(self):
        self.rndState = rnd.getstate()
    def restoreRnd(self, addState=0):
        """ NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple """
        rnd.setstate(self.rndState)
        for i in range(addState): rnd.random()

    #-------------------------------------------------------------------

    def setAll(self, life= 1.0):
        for l in self.links.links_Cell_Cell:
            l.reset(life)

    def stepAll(self):
        for key,l in self.links.link_map.items():
            l.degrade(self.deg)

    #-------------------------------------------------------------------

    def step(self, subSteps = 10):
        if not self.links.links_Air_Cell:
            DEV.log_msg(f"Found no entry links!", {"SIM", "ERROR"})
            return

        # get entry
        self.entry = self.current = self.get_entryLink(self.links.links_Air_Cell)

        # logging step info
        self.id_step += 1
        if (self.log):
            self.stepInfo = StepInfo()
            self.simInfo.append(self.stepInfo)

        # main loop
        for i in range(subSteps):
            self.id_substep += 1

            # logging path info
            if (self.log):
                self.subInfo = StepInfo()
                self.stepInfo.sub.append(self.subInfo)

            # WIP:: choose link to propagate
            self.current = self.get_nextLink(self.current)

            # WIP:: degrade should be a bit rnd etc
            self.apply_degradation(self.current)

            # WIP:: break condition, no substep count
            if False: break


    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self, entries:list[Link]) -> Link:
        weights = [ self.get_entryWeight(el) for el in entries ]
        pick = rnd.choices(entries, weights)[0]
        return pick

    def get_entryWeight(self, el:Link):
        w = 1
        #w = 0
        #w += max(el.pos.y * 10, 0)
        #w += abs(l.pos.z) * 100
        #if l.pos != 0: w = 0
        #if abs(el.dir.z) > 0.2: w = 0
        return w

    #-------------------------------------------------------------------

    def get_nextLink(self, cl:Link) -> Link:
        weights = [ self.get_nextWeight(cl) for cl in cl.neighs_Cell_Cell ]
        pick = rnd.choices(cl.neighs_Cell_Cell, weights)[0]
        return pick

    def get_nextWeight(self, cl):
        w = 1
        #w = 1 if not cl.airLink else 0
        #if l.life != 1: w = 0
        #return max(0, w)
        return w

    #-------------------------------------------------------------------

    def apply_degradation(self, cl:Link):
        cl.degrade(self.deg)

def resetLife(links: LinkCollection, life = 1.0):
    for i,l in enumerate(links.links_Cell_Cell):
        l.life = life