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

class SubStepData:
    """ Information per sub step """
    def __init__(self):
        self.currentL             : Link        = None
        self.currentL_life        : float       = None
        self.currentL_deg         : float       = None
        self.currentL_candidates  : list[Link]  = None
        self.currentL_candidatesW : list[float] = None
        self.waterLevel           : float       = None
        self.waterLevel_deg       : float       = None

class StepData:
    """ Information per step """
    def __init__(self):
        self.subs               : list[SubStepData] = list()
        self.entryL             : Link              = None
        self.entryL_candidates  : list[Link]        = None
        self.entryL_candidatesW : list[float]       = None
        self.exitL              : Link              = None
        self.break_msg          : str               = "no-break"

class SIM_CONST:
    """ #WIP:: Some sim constants, maybe moved """
    upY = Vector((0,1,0))
    backZ = Vector((0,0,-1))
    dot_aligned_threshold = 1-1e-6

    def aligned(v1:Vector, v2:Vector, bothDir = False):
        return SIM_CONST.aligned_min(v1,v2,SIM_CONST.dot_aligned_threshold, bothDir)

    def aligned_min(v1:Vector, v2:Vector, minDot:float, bothDir = False):
        d = v1.dot(v2)
        if bothDir: d = abs(d)
        return d > minDot

    def aligned_max(v1:Vector, v2:Vector, maxDot:float, bothDir = False):
        d = v1.dot(v2)
        if bothDir: d = abs(d)
        return d < maxDot

# TODO:: edit in UI some panel
class SIM_CFG:
    """ Sim config values to tweak """
    test = False

    entryL_min_align = 0.1
    nextL_min_align = 0.1

    water_baseCost = 0.005
    water_linkCost = 0.1
    water_minAbsorb_check = 0.33
    water_minAbsorb_continueProb = 0.9

    # add test, deg, log, etc here

#-------------------------------------------------------------------

class Simulation:
    def __init__(self, links_initial: LinkCollection, deg = 0.05, log = True, test = True):
        self.storeRnd()
        SIM_CFG.test2D = test

        self.links             = links_initial
        self.links_iniLife     = [ l.life for l in self.links.links_Cell_Cell ]
        self.links_iniLife_air = [ l.life for l in self.links.links_Air_Cell  ]
        self.deg               = deg

        self.entryL              : Link  = None
        self.currentL            : Link  = None
        self.currentL_areaFactor : float = 1.0
        self.waterLevel          : float = 1.0

        self.trace      : bool           = log
        self.trace_data : list[StepData] = list()
        self.step_trace : StepData       = None
        self.sub_trace  : SubStepData    = None
        self.step_id = self.sub_id = -1

    def set_deg(self, deg):
        self.deg = deg

    def resetSim(self, addSeed = 0, initialAirToo = True):
        self.restoreRnd(addSeed)

        # WIP:: should use reset function etc
        for i,l in enumerate(self.links.links_Cell_Cell):
            l.reset(self.links_iniLife[i])
        if initialAirToo:
            for i,l in enumerate(self.links.links_Air_Cell):
                l.reset(self.links_iniLife_air[i])

        # reset currents
        self.entryL              : Link  = None
        self.currentL            : Link  = None
        self.currentL_areaFactor : float = 1.0
        self.waterLevel          : float = 1.0

        # reset log
        if self.trace:
            self.trace_data.clear()
            self.step_trace = None
            self.sub_trace = None
            self.step_id = self.sub_id = -1

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
        # TODO:: improve this, also src of slowness?
        if (self.trace):
            self.step_id += 1
            self.step_trace = StepData()
            self.trace_data.append(self.step_trace)
        else: inlineLog = False

        # get entry and degrade it some amount (visual change + step counter)
        self.get_entryLink()
        if self.entryL:
            self.currentL = self.entryL
            self.entryL.degrade(self.deg*10)

        # LOG entry
        if inlineLog:
            DEV.log_msg(f" > ({self.step_id})   : entry {self.step_trace.entryL}"
                        f" : n{len(self.step_trace.entryL_candidates)} {self.step_trace.entryL_candidatesW}",
                        {"SIM", "LOG", "STEP"}, cut=False)
            if SIM_CFG.test2D:
                DEV.log_msg(f" > ({self.step_id})   : TEST flag set", {"SIM", "LOG", "STEP"})


        # main loop with a break condition
        for i in range(subSteps):
            if not self.check_continue(): break

            # logging path info
            if (self.trace):
                self.sub_id += 1
                self.sub_trace = SubStepData()
                self.step_trace.subs.append(self.sub_trace)

            # choose next link to propagate
            self.get_nextLink()
            self.currentL_areaFactor = self.currentL.area / self.links.avg_area

            # apply degradation etc
            if self.currentL:
                self.link_degradation()
                self.water_degradation()

                # LOG inline during loop
                if inlineLog:
                    DEV.log_msg(f" > ({self.step_id},{self.sub_id}) : {self.sub_trace.currentL}"
                            f" d({self.sub_trace.currentL_deg:.3f})"
                            f" : n{len(self.sub_trace.currentL_candidates)} {self.sub_trace.currentL_candidatesW}",
                            {"SIM", "LOG", "SUB"}, cut=False)


        # LOG exit
        if (self.trace):
            self.step_trace.exitL = self.currentL
        if inlineLog:
            DEV.log_msg(f" > ({self.step_id})   : exit {self.step_trace.exitL} ({self.step_trace.break_msg})", {"SIM", "LOG", "STEP"})


    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self):
        candidates = self.links.links_Air_Cell

        # candidates not found
        if not candidates:
            self.entryL = None
            weights = []

        # rnd.choices may fail due to all weights being null etc
        else:
            weights = [ self.get_entryWeight(l) for l in candidates ]
            try:
                picks = rnd.choices(candidates, weights)
                self.entryL = picks[0]

            except ValueError:
                self.entryL = None

        # continuous trace data
        if self.trace:
            self.step_trace.entryL = self.entryL
            self.step_trace.entryL_candidates = candidates
            self.step_trace.entryL_candidatesW = weights

    def get_entryWeight(self, l:Link):
        if SIM_CFG.test2D:
            # WIP:: limit axis for the hill model
            if SIM_CONST.aligned(l.dir, SIM_CONST.backZ, bothDir=True):
                return 0

        # IDEA:: maybe shift vector a bit by some wind factor?
        water_dir_inv = SIM_CONST.upY

        # cut-off min align
        d = l.dir.dot(water_dir_inv)
        if d < SIM_CFG.entryL_min_align:
            w = 0

        # weight using face area
        else:
            w = d * l.area

        return w

    #-------------------------------------------------------------------

    def get_nextLink(self):
        # merge neighs, the water could scape to the outer surface
        candidates = self.currentL.neighs_Cell_Cell + self.currentL.neighs_Air_Cell

        # candidates not found
        if not candidates:
            self.currentL = None
            weights = []

        # rnd.choices may fail due to all weights being null etc
        else:
            weights = [ self.get_nextWeight(l) for l in candidates ]
            try:
                picks = rnd.choices(candidates, weights)
                self.currentL = picks[0]

            except ValueError:
                self.currentL = None

        # continuous trace data
        if self.trace:
            self.sub_trace.currentL = self.currentL
            self.sub_trace.currentL_candidates = candidates
            self.sub_trace.currentL_candidatesW = weights

    def get_nextWeight(self, l:Link):
        if SIM_CFG.test2D:
            # WIP:: limit axis for the hill model also for next links (e.g. exit wall links)
            if SIM_CONST.aligned(l.dir, SIM_CONST.backZ, bothDir=True):
                return 0

        # original uniform probability
        w = 1

        # relative direction cannot go up
        # WIP:: should diff from edge that connects not parent link center
        dpos = l.pos - self.currentL.pos
        if not SIM_CONST.aligned_min(dpos.normalized(), -SIM_CONST.upY, SIM_CFG.nextL_min_align):
            w = 0

        return w

    #-------------------------------------------------------------------

    def link_degradation(self):
        # calcultate degradation
        d = self.deg * self.waterLevel

        # apply degradation
        self.currentL.degrade(d)
        # TODO:: trigger breaking?

        if self.trace:
            self.sub_trace.currentL_life = self.currentL.life
            self.sub_trace.currentL_deg = d


    def water_degradation(self):
        # minimun degradation that also happens when the water runs through a exterior face
        d = SIM_CFG.water_baseCost * self.currentL_areaFactor

        # interior also takes into account current link life
        if not self.currentL.airLink:
            d += SIM_CFG.water_linkCost * self.currentL.life_clamped

        self.waterLevel -= d

        # check complete water absortion event
        if self.waterLevel < SIM_CFG.water_minAbsorb_check:
            minAbsorb = self.waterLevel / SIM_CFG.water_minAbsorb_check
            if minAbsorb * SIM_CFG.water_minAbsorb_continueProb < rnd.random():
                self.waterLevel = -1

        if self.trace:
            self.sub_trace.waterLevel = self.currentL.life
            self.sub_trace.waterLevel_deg = d


    def check_continue(self):
        # no next link was found
        if not self.currentL:
            if self.trace: self.step_trace.break_msg = "NO_LINK"
            return False

        # not more water
        if self.waterLevel < 0:
            if self.trace: self.step_trace.break_msg = "NO_WATER"
            return False

        return True

# WIP:: simulation instance only resides in the OP -> move to MWcont and share across OP invokes
def resetLife(links: LinkCollection, life = 1.0):
    for l in links.link_map.values():
        l.reset()