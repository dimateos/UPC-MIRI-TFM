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

        # empty trace data
        self.step_reset()
        self.step_reset_trace()

    def reset(self, rnd = False):
        # reset links and cells
        if rnd: self.reset_state_rnd()
        else: self.reset_state()

        self.step_reset()
        self.step_reset_trace()

    def rnd_store(self, genNew = True):
        """ Store the random state """
        if genNew: rnd.random()
        self.rndState = rnd.getstate()

    def rnd_restore(self, addState=0):
        """ # NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple """
        utils.debug_rnd_seed(addState)
        #rnd.setstate(self.rndState)
        #for i in range(addState): rnd.random()

    #-------------------------------------------------------------------

    def backup_state(self):
        # delegate backup to the links
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.backup_state()

        # store cells state too
        self.cont.backupState()

    def backup_state_restore(self):
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.backupState_restore()

        self.cont.backupState_restore()

        # global recalculation including graphs
        self.links.comps_recalc()

    def reset_state(self, life=1.0, picks=0):
        # modify links direclty
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.reset(life, picks)

        # reset cells
        self.cont.reset()

        # global recalculation including graphs
        self.links.comps_recalc()

    def reset_state_rnd(self, min_val=0, max_val=1, max_picks = 8, max_entry = 8):
        # modify links direclty
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            r = lambda : rnd.random() * (max_val-min_val) + min_val
            life = r()
            picks = int(r()*max_picks)
            entry = int(r()*self.get_entryWeight(l)*max_entry)
            l.reset(life, picks, entry)

        # reset cells normally
        self.cont.reset()

        # global recalculation including graphs
        self.links.comps_recalc()

    #-------------------------------------------------------------------

    def step_reset(self):
        self.entryL     : Link  = None
        self.currentL   : Link  = None
        self.waterLevel : float = self.cfg.step_waterIn
        self.exit_msg   : str = ""
        self.step_path  : list[Link] = []

    def step_reset_trace(self):
        self.step_id = self.step_depth = -1
        self.trace_data : list[StepData] = list()
        self.step_trace : StepData       = None
        self.sub_trace  : SubStepData    = None

    def step_degradeAll(self):
        for l in self.links.internal:
            l.degrade(self.cfg.step_linkDeg)

    def step(self):
        self.step_reset()
        self.step_id += 1

        # LOG: initial water
        if self.cfg.debug_log:
            DEV.log_msg(f" > ({self.step_id}) : starting waterLevel {self.waterLevel}", {"SIM", "STEP"}, cut=False)

        # TRACE: writing the full trace slows down the process, even more when print to console!
        if (self.cfg.debug_simTrace):
            self.step_trace = StepData()
            self.trace_data.append(self.step_trace)
        trace_log = self.cfg.debug_log and self.cfg.debug_simTrace


        # get entry
        self.get_entryLink()

        # LOG: entry
        if self.cfg.debug_log:
            DEV.log_msg(f" > ({self.step_id}) : L ({self.currentL})", {"SIM", "ENTRY"}, cut=False)
        # TRACE: log entry
        if trace_log:
            DEV.log_msg(f" : n{len(self.step_trace.entryL_candidates)} {self.step_trace.entryL_candidatesW}",
                        {"SIM", "ENTRY", "TRACE"}, cut=False)


        # main loop with a break condition
        self.infiltration_loop(trace_log)


        # LOG: exit
        if self.cfg.debug_log:
            DEV.log_msg(f" >>> len({len(self.step_path)}) : {self.step_path}", {"SIM", "PATH"}, cut=False)
            DEV.log_msg(f" > ({self.step_id}) : {self.exit_msg} : L ({self.currentL})", {"SIM", "EXIT"}, cut=False)

        # TRACE: log step
        if (self.cfg.debug_simTrace):
            self.step_trace.exitL = self.currentL
        if trace_log:
            DEV.log_msg(f" : n{len(self.sub_trace.currentL_candidates)} {self.sub_trace.currentL_candidatesW[:32]}",
                        {"SIM", "EXIT", "TRACE"}, cut=False)


    def infiltration_loop(self, trace_log=False):
        self.step_depth = -1
        while self.check_continue():
            self.step_depth += 1

            # TRACE: build step
            if (self.cfg.debug_simTrace):
                self.sub_trace = SubStepData()
                self.step_trace.subs.append(self.sub_trace)

            # choose next link to propagate
            self.get_nextLink()

            # apply degradation etc
            if self.currentL:
                self.water_degradation()
                self.link_degradation()

                # TRACE: log step
                if trace_log:
                    DEV.log_msg(f" > ({self.step_id},{self.step_depth}) : w({self.sub_trace.waterLevel:.3f})"
                            f" : dw({self.sub_trace.waterLevel_deg:.3f}) dl({self.sub_trace.currentL_deg:.3f})"
                            f" : {self.sub_trace.currentL}"
                            f" : n{len(self.sub_trace.currentL_candidates)} {self.sub_trace.currentL_candidatesW[:32]}",
                            {"SIM", "SUB", "TRACE"}, cut=False)

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

        # found an entry
        if self.entryL:
            self.currentL = self.entryL
            self.step_path.append(self.currentL.key_cells)

        # TRACE: build entry
        if self.cfg.debug_simTrace:
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

        # found the next
        if self.entryL:
            self.step_path.append(self.currentL.key_cells)

        # TRACE: build next
        if self.cfg.debug_simTrace:
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
        d = self.cfg.step_linkDeg * self.waterLevel

        # apply degradation -> potential break
        if (self.currentL.degrade(d)):
            pass
            #self.links.setState_link_check(self.currentL.key_cells)

        # TRACE: build deg
        if self.cfg.debug_simTrace:
            self.sub_trace.currentL_life = self.currentL.life
            self.sub_trace.currentL_deg = d

    def water_degradation(self):
        # minimun degradation that also happens when the water runs through a exterior face
        d = self.cfg.water_baseCost * self.currentL.area * self.currentL.resistance

        # interior also takes into account current link life
        if self.currentL.state == LINK_STATE_ENUM.SOLID:
            d += self.cfg.water_linkCost * self.currentL.area * self.currentL.life_clamped

        self.waterLevel -= d

        if self.cfg.debug_simTrace:
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
            self.exit_msg = "NO_LINK"

        # no more water
        if self.waterLevel < 0:
            if self.waterLevel == -1: self.exit_msg = "NO_WATER_RND"
            else: self.exit_msg = "NO_WATER"

        # max iterations when enabled
        if self.cfg.step_maxDepth and self.step_depth >= self.cfg.step_maxDepth-1:
            self.exit_msg = "MAX_ITERS"

        # found msg means exit condition was met
        if self.exit_msg:
            # TRACE: keep msg per trace
            if self.cfg.debug_simTrace:
                self.step_trace.break_msg = self.exit_msg
            return False

        # continue sim when no exit msg recorded
        return True
