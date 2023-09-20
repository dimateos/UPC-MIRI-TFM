import bpy.types as types
from mathutils import Vector, Matrix
import random as rnd

from .preferences import getPrefs
from .properties import (
    MW_sim_cfg,
)

from .mw_cont import MW_Cont
from .mw_links import MW_Links, Link, LINK_STATE_ENUM

from . import utils, utils_trans
from .utils_trans import VECTORS
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------
# IDEA:: toggle full log / etc
# IDEA:: vis step_infiltrations with a curve
# IDEA:: vis probs with a heatmap
# IDEA:: manually pick step/ entry? by num?
# IDEA:: run until break
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

#-------------------------------------------------------------------

class MW_Sim:
    def __init__(self, cont: MW_Cont, links: MW_Links):
        self.cfg : MW_sim_cfg = cont.root.mw_sim
        self.cont : MW_Cont = cont
        self.links : MW_Links = links

        #self.links_iniLife     = [ l.life for l in self.links.internal ]
        #self.links_iniLife_air = [ l.life for l in self.links.external ]

        self.step_reset()
        self.step_id = self.sub_id = -1

        self.trace_data : list[StepData] = list()
        self.step_trace : StepData       = None
        self.sub_trace  : SubStepData    = None

    def reset(self, debug_addSeed = 0, initialAirToo = True):
        #self.rnd_restore(debug_addSeed)
        self.reset_links()

        self.step_reset()
        self.step_id = self.sub_id = -1

        # reset log
        if self.cfg.debug_trace:
            self.trace_data.clear()
            self.step_trace = None
            self.sub_trace  = None

    def rnd_store(self):
        self.rndState = rnd.getstate()
    def rnd_restore(self, addState=0):
        """ # NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple """
        utils.debug_rnd_seed(addState)
        #rnd.setstate(self.rndState)
        #for i in range(addState): rnd.random()

    #-------------------------------------------------------------------

    def reset_links(self, life=1.0, picks=0):
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.reset(life, picks)

    def reset_links_rnd(self, min_val=0, max_val=1, max_picks = 8, max_entry = 8):
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            r = lambda : rnd.random() * (max_val-min_val) + min_val
            life = r()
            picks = int(r()*max_picks)
            entry = int(r()*self.get_entryWeight(l)*max_entry)
            l.reset(life, picks, entry)

    #-------------------------------------------------------------------

    def step_reset(self):
        self.entryL              : Link  = None
        self.currentL            : Link  = None
        self.waterLevel          : float = 1.0

    def step_all(self):
        for l in self.links.internal:
            l.degrade(self.cfg.step_deg)

    def step(self):
        self.step_reset()
        self.step_id += 1

        # writing the full trace slows down the process, even more when print to console!
        if (self.cfg.debug_trace):
            inlineLog = self.cfg.debug_log
            self.step_trace = StepData()
            self.trace_data.append(self.step_trace)
        else:
            inlineLog = False

        # get entry and degrade it some amount (visual change + step counter)
        self.get_entryLink()
        if self.entryL:
            self.currentL = self.entryL

        # LOG entry
        if inlineLog:
            DEV.log_msg(f" > ({self.step_id}) : entry {self.step_trace.entryL}"
                        f" : n{len(self.step_trace.entryL_candidates)} {self.step_trace.entryL_candidatesW}",
                        {"SIM", "LOG", "STEP"}, cut=False)


        # main loop with a break condition
        self.sub_id = -1
        while self.check_continue():
            self.sub_id += 1
            if (self.cfg.debug_trace):
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
        if (self.cfg.debug_trace):
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
                self.entryL.picks_entry +=1

            except ValueError as e:
                self.entryL = None

        # continuous trace data
        if self.cfg.debug_trace:
            self.step_trace.entryL = self.entryL
            self.step_trace.entryL_candidates = candidates
            self.step_trace.entryL_candidatesW = weights

    def get_entryWeight(self, l:Link):
        #if MW_Links.skip_link_debugModel(l): return 0 # just not generated

        # link dir align (face normal)
        w = self.get_entryAlign(l.dir)

        # weight using face area (normalized)
        if self.cfg.link_entry_areaWeigthed:
            w*= l.area

        return w

    def get_entryAlign(self, vdir:Vector, bothDir=False):
        # relative position water dir
        water_dir_inv = -self.cfg.water_entry_dir.normalized()
        d = vdir.dot(water_dir_inv)
        if bothDir: d = abs(d)

        # cut-off
        if d < self.cfg.link_entry_minAlign:
            return 0
        return d

    #-------------------------------------------------------------------

    def get_nextLink(self):
        # merge neighs, the water could scape to the outer surface
        candidates = self.links.get_link_neighs(self.currentL.key_cells)

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
                self.currentL.picks += 1

            except ValueError as e:
                self.currentL = None

        # continuous trace data
        if self.cfg.debug_trace:
            self.sub_trace.currentL = self.currentL
            self.sub_trace.currentL_candidates = candidates
            self.sub_trace.currentL_candidatesW = weights

    def get_nextWeight(self, l:Link):
        #if MW_Links.skip_link_debugModel(l): return 0 # just not generated

        # relative pos align
        dpos = l.pos - self.currentL.pos
        w = self.get_nextAlign(dpos.normalized())

        # check link resistance field
        r = 1 - l.resistance
        w *= r

        return max(w, 0.0001)

    def get_nextAlign(self, vdir:Vector, bothDir=False):
        # relative pos align
        water_dir_inv = -VECTORS.upZ
        d = vdir.normalized().dot(water_dir_inv)
        if bothDir: d = abs(d)

        # cut-off
        if d < self.cfg.link_next_minAlign:
            return 0
        return d

    #-------------------------------------------------------------------

    def link_degradation(self):
        # calcultate degradation
        d = self.cfg.step_deg * self.waterLevel

        # apply degradation -> potential break
        if (self.currentL.degrade(d)):
            self.links.check_link_break(self.currentL.key_cells)

        if self.cfg.debug_trace:
            self.sub_trace.currentL_life = self.currentL.life
            self.sub_trace.currentL_deg = d

    def water_degradation(self):
        # minimun degradation that also happens when the water runs through a exterior face
        d = self.cfg.water_baseCost * self.currentL.area * self.currentL.resistance

        # interior also takes into account current link life
        if self.currentL.state == LINK_STATE_ENUM.SOLID:
            d += self.cfg.water_linkCost * self.currentL.area * self.currentL.life_clamped

        self.waterLevel -= d

        if self.cfg.debug_trace:
            self.sub_trace.waterLevel = self.waterLevel
            self.sub_trace.waterLevel_deg = d

        # check complete water absortion event
        if self.waterLevel < self.cfg.water_minAbsorb_check and self.waterLevel > 0:
            minAbsorb = self.waterLevel / self.cfg.water_minAbsorb_check
            if minAbsorb * self.cfg.water_minAbsorb_continueProb < rnd.random():
                self.waterLevel = -1

        # TODO:: degradation before or after cost?

    #-------------------------------------------------------------------

    def check_continue(self):
        # no next link was found
        if not self.currentL:
            if self.cfg.debug_trace:
                self.step_trace.break_msg = "NO_LINK"
            return False

        # no more water
        if self.waterLevel < 0:
            if self.cfg.debug_trace:
                if self.waterLevel == -1: self.step_trace.break_msg = "NO_WATER_RND"
                else: self.step_trace.break_msg = "NO_WATER"
            return False

        # max iterations when enabled
        if self.cfg.step_maxDepth and self.sub_id >= self.cfg.step_maxDepth-1:
            if self.cfg.debug_trace:
                self.step_trace.break_msg = "MAX_ITERS"
            return False

        return True
