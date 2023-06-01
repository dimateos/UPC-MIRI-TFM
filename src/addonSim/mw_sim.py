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

# IDEA:: bridges neighbours? too aligned wall links, vertically aligned internal -> when broken? cannot go though?

class SubStepInfo:
    """ Information per sub step """
    def __init__(self):
        self.current_pick   : Link        = None
        self.neighs         : list[Link]  = None
        self.neighs_weights : list[float] = None
        self.current_life   : float       = None
        self.current_deg    : float       = None

class StepInfo:
    """ Information per step """
    def __init__(self):
        self.sub             : list[SubStepInfo] = list()
        self.entry_pick      : Link              = None
        self.entries         : list[Link]        = None
        self.entries_weights : list[float]       = None
        self.current_exit    : Link              = None
        self.break_exit      : bool              = False
        self.break_msg       : str               = None

class SIM_CONST:
    """ #WIP:: Some sim constants, maybe moved """
    upY = Vector((0,1,0))
    backZ = Vector((0,0,-1))
    dot_align_threshold = 1-1e-6

    def aligned(v1:Vector, v2:Vector, bothDir = False):
        return SIM_CONST.aligned_min(v1,v2,SIM_CONST.dot_align_threshold, bothDir)

    def aligned_min(v1:Vector, v2:Vector, minDot:float, bothDir = False):
        d = v1.dot(v2)
        if bothDir: d = abs(d)
        return d > minDot

    def aligned_max(v1:Vector, v2:Vector, maxDot:float, bothDir = False):
        d = v1.dot(v2)
        if bothDir: d = abs(d)
        return d < maxDot


class SIM_CFG:
    """ Sim config values to tweak """
    test = False

    entry_minY_align = 0.1
    next_minY_align = 0.1

#-------------------------------------------------------------------

class Simulation:
    def __init__(self, links_initial: LinkCollection, deg = 0.05, log = True, test = True):
        self.storeRnd()
        SIM_CFG.test2D = test

        self.links           = links_initial
        self.initial_life    = [ l.life for l in self.links.links_Cell_Cell ]
        self.initialAir_life = [ l.life for l in self.links.links_Air_Cell  ]
        self.deg             = deg

        self.entry    : Link           = None
        self.current  : Link           = None

        self.log      : bool           = log
        self.simInfo  : list[StepInfo] = list()
        self.stepInfo : StepInfo       = None
        self.subInfo  : SubStepInfo    = None
        self.id_step = self.id_substep = -1

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

        # get entry and degrade it to increase its stepped counter
        self.entry = self.current = self.get_entryLink(entries)
        self.entry.degrade(self.deg*10)

        # LOG entry
        if inlineLog:
            DEV.log_msg(f" > ({self.id_step})   : entry {self.stepInfo.entry_pick}"
                        f" : n{len(self.stepInfo.entries)} {self.stepInfo.entries_weights}",
                        {"SIM", "LOG", "STEP"}, cut=False)
            if SIM_CFG.test2D:
                DEV.log_msg(f" > ({self.id_step})   : TEST flag set", {"SIM", "LOG", "STEP"})

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
            if self.current:
                self.apply_degradation(self.current)

            # WIP:: break condition
            if not self.current or False:
                self.stepInfo.break_exit = True
                self.stepInfo.break_msg = "NO_NEIGH"
                break

            # LOG inline during loop
            if inlineLog:
                DEV.log_msg(f" > ({self.id_step},{self.id_substep}) : {self.subInfo.current_pick}"
                        f" d({self.subInfo.current_deg:.3f})"
                        f" : n{len(self.subInfo.neighs)} {self.subInfo.neighs_weights}",
                        {"SIM", "LOG", "SUB"}, cut=False)
                #self.subInfo

        # LOG exit
        if (self.log):
            self.stepInfo.current_exit = self.current
        if inlineLog:
            DEV.log_msg(f" > ({self.id_step})   : exit {self.stepInfo.current_exit}", {"SIM", "LOG", "STEP"})
            if self.stepInfo.break_exit:
                DEV.log_msg(f" > ({self.id_step})   : break {self.stepInfo.break_msg}", {"SIM", "LOG", "STEP"})
            #self.stepInfo


    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self, entries:list[Link]) -> Link:
        weights = [ self.get_entryWeight(el) for el in entries ]
        picks = rnd.choices(entries, weights)

        # there should always be a pick from existing entry links
        #if not picks: return None
        pick = picks[0]

        # continuous trace info
        if self.log:
            self.stepInfo.entry_pick = pick
            self.stepInfo.entries = entries
            self.stepInfo.entries_weights = weights

        return pick

    def get_entryWeight(self, el:Link):
        w = 1

        # face aligned upwards
        # WIP:: same as just reading the normalized Y component?
        #if not SIM_CONST.aligned_min(el.dir, SIM_CONST.upY, SIM_CFG.entry_minY_align):
        if el.dir.y < SIM_CFG.entry_minY_align:
            w = 0

        # WIP:: limit axis for the hill model (same as reading Z component)?
        if SIM_CFG.test2D:
            if SIM_CONST.aligned(el.dir, SIM_CONST.backZ, bothDir=True):
                w = 0

        return w

    #-------------------------------------------------------------------

    def get_nextLink(self, cl:Link) -> Link:
        # merge neighs, the water could scape to the outer surface
        neighs = cl.neighs_Cell_Cell + cl.neighs_Air_Cell

        if not neighs:
            return None

        weights = [ self.get_nextWeight(cl, nl) for nl in neighs ]

        # choices may fail
        try:
            picks = rnd.choices(neighs, weights)
            pick = picks[0]

        # picks empty or no cumulative weights
        except ValueError:
            return None

        # continuous trace info
        if self.log:
            self.subInfo.current_pick = pick
            self.subInfo.neighs = neighs
            self.subInfo.neighs_weights = weights

        return pick

    def get_nextWeight(self, cl:Link, nl:Link):
        w = 1

        # relative direction cannot go up
        # WIP:: should diff from edge that connects not parent link center
        dpos = nl.pos - cl.pos
        if not SIM_CONST.aligned_min(dpos.normalized(), -SIM_CONST.upY, SIM_CFG.next_minY_align):
            w = 0

        # WIP:: limit axis for the hill model also for next links as they can pick walls to exit
        if SIM_CFG.test2D:
            if SIM_CONST.aligned(nl.dir, SIM_CONST.backZ, bothDir=True):
                w = 0

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