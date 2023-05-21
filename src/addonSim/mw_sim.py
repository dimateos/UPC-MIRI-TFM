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
# IDEA:: vis steps with a curve
# IDEA:: vis probs with a heatmap
# IDEA:: manually pick step/ entry? by num?
# IDEA:: pass/reuse cfg sim direclty maybe also for mwcont?

class SubStepInfo:
    def __init__(self):
        self.current_pick   : Link        = None
        self.neighs         : list[Link]  = None
        self.neighs_weights : list[float] = None
        self.current_life   : float       = None
        self.current_deg    : float       = None

class StepInfo:
    def __init__(self):
        self.sub             : list[SubStepInfo] = list()
        self.entry_pick      : Link              = None
        self.entries         : list[Link]        = None
        self.entries_weights : list[float]       = None
        self.current_exit    : Link              = None

class SIM_CONSTANTS:
    up = Vector((0,1,0))
    dev_upAlign = 0.2

#-------------------------------------------------------------------

class Simulation:
    def __init__(self, links_initial: LinkCollection, deg = 0.05, log = True, test = True):
        self.storeRnd()

        self.links           = links_initial
        self.initial_life    = [ l.life for l in self.links.links_Cell_Cell ]
        self.initialAir_life = [ l.life for l in self.links.links_Air_Cell ]
        self.deg             = deg

        self.entry    : Link           = None
        self.current  : Link           = None

        self.log      : bool           = log
        self.simInfo  : list[StepInfo] = list()
        self.stepInfo : StepInfo       = None
        self.subInfo  : SubStepInfo    = None
        self.id_step = self.id_substep = -1
        self.test     :bool            = test

    def set_deg(self, deg):
        self.deg = deg

    def resetSim(self, addSeed = 0, initialAirToo = True):
        self.restoreRnd(addSeed)

        # WIP:: should use reset function etc
        for i,l in enumerate(self.links.links_Cell_Cell):
            l.reset(self.initial_life[i])
        if initialAirToo:
            for i,l in enumerate(self.links.links_Air_Cell):
                l.reset(self.initialAir_life[i])

        if self.log:
            self.simInfo.clear()
            self.stepInfo = None
            self.subInfo = None
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
        for l in self.links.links_Cell_Cell:
            l.degrade(self.deg)

    #-------------------------------------------------------------------

    def step(self, subSteps = 10, inlineLog = True):
        entries = self.links.links_Air_Cell
        if not entries:
            DEV.log_msg(f"Found no entry links!", {"SIM", "ERROR"})
            return

        # logging step info
        self.id_step += 1
        if (self.log):
            self.stepInfo = StepInfo()
            self.simInfo.append(self.stepInfo)

        # get entry
        self.entry = self.current = self.get_entryLink(entries)
        if inlineLog:
            DEV.log_msg(f" > ({self.id_step})   : entry {self.stepInfo.entry_pick}"
                        f" : n{len(self.stepInfo.entries)} {self.stepInfo.entries_weights}",
                        {"SIM", "LOG", "STEP"}, cut=False)


        # main loop
        for i in range(subSteps):
            self.id_substep += 1

            # logging path info
            if (self.log):
                self.subInfo = SubStepInfo()
                self.stepInfo.sub.append(self.subInfo)

            # WIP:: choose link to propagate
            self.current = self.get_nextLink(self.current)

            # WIP:: degrade should be a bit rnd etc
            self.apply_degradation(self.current)

            # WIP:: break condition, no substep count
            if False: break


            # LOG inline during loop
            if inlineLog:
                DEV.log_msg(f" > ({self.id_step},{self.id_substep}) : {self.subInfo.current_pick}"
                        f" d({self.subInfo.current_deg:.3f})"
                        f" : n{len(self.subInfo.neighs)} {self.subInfo.neighs_weights}",
                        {"SIM", "LOG", "SUB"}, cut=True)
                #self.subInfo

        if (self.log):
            self.stepInfo.current_exit = self.current
        if inlineLog:
            DEV.log_msg(f" > ({self.id_step})   : exit {self.stepInfo.current_exit}", {"SIM", "LOG", "STEP"})
            #self.stepInfo


    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self, entries:list[Link]) -> Link:
        weights = [ self.get_entryWeight(el) for el in entries ]
        pick = rnd.choices(entries, weights)[0]
        pick.life += 1

        if self.log:
            self.stepInfo.entry_pick = pick
            self.stepInfo.entries = entries
            self.stepInfo.entries_weights = weights

        return pick

    def get_entryWeight(self, el:Link):
        w = 1

        # WIP:: limit axis for the hill model
        if self.test:
            if el.dir.dot(SIM_CONSTANTS.up) < SIM_CONSTANTS.dev_upAlign:
                w=0

        # IDEA:: face area aligned with gravity
        return w

    #-------------------------------------------------------------------

    def get_nextLink(self, cl:Link) -> Link:
        neighs = cl.neighs_Cell_Cell
        weights = [ self.get_nextWeight(cl) for cl in neighs ]
        pick = rnd.choices(neighs, weights)[0]

        if self.log:
            self.subInfo.current_pick = pick
            self.subInfo.neighs = neighs
            self.subInfo.neighs_weights = weights

        return pick

    def get_nextWeight(self, cl):
        w = 1
        #w = 1 if not cl.airLink else 0
        #if l.life != 1: w = 0
        #return max(0, w)
        return w

    #-------------------------------------------------------------------

    def apply_degradation(self, cl:Link):
        d = self.deg

        if self.log:
            self.subInfo.current_life = cl.life
            self.subInfo.current_deg = d

        cl.degrade(d)

# WIP:: simulation instance only resides in the OP -> move to MWcont and share across OP invokes
def resetLife(links: LinkCollection, life = 1.0):
    for l in links.link_map.values():
        l.reset()