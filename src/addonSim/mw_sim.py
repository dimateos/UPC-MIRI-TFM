import bpy.types as types
from mathutils import Vector, Matrix
import random as rnd

from .preferences import getPrefs

from .mw_links import MW_Links, Link

from . import utils
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------
# IDEA:: toggle full log / etc
# IDEA:: vis step_infiltrations with a curve
# IDEA:: vis probs with a heatmap
# IDEA:: manually pick step/ entry? by num?

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
        self.break_msg          : str               = "NO_BREAK"

class SIM_CONST:
    """ # WIP:: Some sim constants, maybe moved """
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
    link_entry_minAlign = 0.1
    link_next_minAlign = -0.1

    water_baseCost = 0.01
    water_linkCost = 0.2
    water_minAbsorb_check = 0.3
    water_minAbsorb_continueProb = 0.9

    # add test, deg, log, etc here

#-------------------------------------------------------------------

class MW_Sim:
    def __init__(self, links_initial: MW_Links, deg = 0.05, log = True):
        self.storeRnd()

        if DEV.DEBUG_MODEL:
            DEV.log_msg(f" > init : DEBUG_MODEL flag set", {"SIM", "LOG", "STEP"})

        self.links             = links_initial
        self.links_iniLife     = [ l.life for l in self.links.internal ]
        self.links_iniLife_air = [ l.life for l in self.links.external  ]
        self.deg               = deg

        self.resetCurrent()
        self.step_id = self.sub_id = -1

        self.trace      : bool           = log
        self.trace_data : list[StepData] = list()
        self.step_trace : StepData       = None
        self.sub_trace  : SubStepData    = None

    def set_deg(self, deg):
        self.deg = deg

    def resetSim(self, debug_addSeed = 0, initialAirToo = True):
        self.restoreRnd(debug_addSeed)

        # WIP:: should use reset function etc
        for i,l in enumerate(self.links.internal):
            l.reset(self.links_iniLife[i])
        if initialAirToo:
            for i,l in enumerate(self.links.external):
                l.reset(self.links_iniLife_air[i])

        self.resetCurrent()
        self.step_id    = self.sub_id = -1

        # reset log
        if self.trace:
            self.trace_data.clear()
            self.step_trace = None
            self.sub_trace  = None

    def resetCurrent(self):
        self.entryL              : Link  = None
        self.currentL            : Link  = None
        self.waterLevel          : float = 1.0

    def storeRnd(self):
        self.rndState = rnd.getstate()
    def restoreRnd(self, addState=0):
        """ # NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple """
        utils.debug_rnd_seed(addState)
        #rnd.setstate(self.rndState)
        #for i in range(addState): rnd.random()

    #-------------------------------------------------------------------

    def setAll(self, life= 1.0):
        for l in self.links.internal:
            l.reset(life)

    def stepAll(self):
        for l in self.links.internal:
            l.degrade(self.deg)

    #-------------------------------------------------------------------

    def step(self, step_maxDepth = 10, inlineLog = True):
        self.resetCurrent()
        self.step_id += 1

        # TODO:: improve this, also src of slowness?
        if (self.trace):
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
            DEV.log_msg(f" > ({self.step_id}) : entry {self.step_trace.entryL}"
                        f" : n{len(self.step_trace.entryL_candidates)} {self.step_trace.entryL_candidatesW}",
                        {"SIM", "LOG", "STEP"}, cut=False)


        # main loop with a break condition
        self.sub_id = -1
        while self.check_continue(step_maxDepth):
            self.sub_id += 1
            if (self.trace):
                self.sub_trace = SubStepData()
                self.step_trace.subs.append(self.sub_trace)

            # choose next link to propagate
            self.get_nextLink()

            # apply degradation etc
            if self.currentL:
                self.water_degradation()
                self.link_degradation()

                # LOG inline during loop
                if inlineLog:
                    DEV.log_msg(f" > ({self.step_id},{self.sub_id}) : w({self.sub_trace.waterLevel:.3f})"
                            f" : dw({self.sub_trace.waterLevel_deg:.3f}) dl({self.sub_trace.currentL_deg:.3f})"
                            f" : {self.sub_trace.currentL}"
                            f" : n{len(self.sub_trace.currentL_candidates)} {self.sub_trace.currentL_candidatesW[:32]}",
                            {"SIM", "LOG", "SUB"}, cut=False)


        # LOG exit
        if (self.trace):
            self.step_trace.exitL = self.currentL
        if inlineLog:
            DEV.log_msg(f" > ({self.step_id}) : exit ({self.step_trace.break_msg})"
                        f": {self.step_trace.exitL}"
                        f" : n{len(self.sub_trace.currentL_candidates)} {self.sub_trace.currentL_candidatesW[:32]}",
                        {"SIM", "LOG", "STEP"}, cut=False)


    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self):
        candidates = self.links.external

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

            except ValueError as e:
                self.entryL = None

        # continuous trace data
        if self.trace:
            self.step_trace.entryL = self.entryL
            self.step_trace.entryL_candidates = candidates
            self.step_trace.entryL_candidatesW = weights

    def get_entryWeight(self, l:Link):
        if DEV.DEBUG_MODEL:
            # WIP:: limit axis for the hill model
            if SIM_CONST.aligned(l.dir, SIM_CONST.backZ, bothDir=True):
                return 0
        w = 1

        # relative position gravity align
        # IDEA:: maybe shift vector a bit by some wind factor?
        water_dir_inv = SIM_CONST.upY
        d = l.dir.dot(water_dir_inv)

        # cut-off
        if d < SIM_CFG.link_entry_minAlign:
            return 0

        # weight using face areaFactor (could use regular area instead)
        w *= d * l.areaFactor

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

            except ValueError as e:
                self.currentL = None

        # continuous trace data
        if self.trace:
            self.sub_trace.currentL = self.currentL
            self.sub_trace.currentL_candidates = candidates
            self.sub_trace.currentL_candidatesW = weights

    def get_nextWeight(self, l:Link):
        if DEV.DEBUG_MODEL:
            # WIP:: limit axis for the hill model also for next links (e.g. exit wall links)
            if SIM_CONST.aligned(l.dir, SIM_CONST.backZ, bothDir=True):
                return 0
        w = 1

        # relative pos align
        water_dir_inv = -SIM_CONST.upY
        dpos = l.pos - self.currentL.pos
        d = dpos.normalized().dot(water_dir_inv)

        # cut-off
        if d < SIM_CFG.link_next_minAlign:
            return 0

        # weight using only the angle
        w *= d

        # check link resistance field
        r = 1 - l.resistance
        w *= r

        return max(w, 0.0001)

    #-------------------------------------------------------------------

    def link_degradation(self):
        # calcultate degradation
        d = self.deg * self.waterLevel

        # apply degradation
        self.currentL.degrade(d)

        if self.trace:
            self.sub_trace.currentL_life = self.currentL.life
            self.sub_trace.currentL_deg = d

        # TODO:: trigger breaking?

    def water_degradation(self):
        # minimun degradation that also happens when the water runs through a exterior face
        d = SIM_CFG.water_baseCost * self.currentL.areaFactor * self.currentL.resistance

        # interior also takes into account current link life
        if not self.currentL.airLink:
            d += SIM_CFG.water_linkCost * self.currentL.areaFactor * self.currentL.life_clamped

        self.waterLevel -= d

        if self.trace:
            self.sub_trace.waterLevel = self.waterLevel
            self.sub_trace.waterLevel_deg = d

        # check complete water absortion event
        if self.waterLevel < SIM_CFG.water_minAbsorb_check and self.waterLevel > 0:
            minAbsorb = self.waterLevel / SIM_CFG.water_minAbsorb_check
            if minAbsorb * SIM_CFG.water_minAbsorb_continueProb < rnd.random():
                self.waterLevel = -1

    #-------------------------------------------------------------------

    def check_continue(self, step_maxDepth):
        # no next link was found
        if not self.currentL:
            if self.trace:
                self.step_trace.break_msg = "NO_LINK"
            return False

        # no more water
        if self.waterLevel < 0:
            if self.trace:
                if self.waterLevel == -1: self.step_trace.break_msg = "NO_WATER_RND"
                else: self.step_trace.break_msg = "NO_WATER"
            return False

        # max iterations when enabled
        if step_maxDepth and self.sub_id >= step_maxDepth-1:
            if self.trace:
                self.step_trace.break_msg = "MAX_ITERS"
            return False

        return True


# WIP:: simulation instance only resides in the OP -> move to MWcont and share across OP invokes
def resetLife(links: MW_Links, life = 1.0):
    for l in links.link_map.values():
        l.reset()