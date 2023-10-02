import bpy.types as types
from mathutils import Vector, Matrix
import random as rnd

from .preferences import getPrefs
from .properties import (
    MW_sim_cfg,
)

from .mw_cont import MW_Cont
from .mw_links import MW_Links, Link, LINK_STATE_ENUM, neigh_key_t

from . import utils, utils_trans
from .utils_trans import VECTORS
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------
# IDEA:: bridges neighbours? too aligned wall links, vertically aligned internal -> when broken? cannot go though?

class SIM_EXIT_FLAG:
    STILL_RUNNING      = -1
    MAX_DEPTH          = 0
    NO_WATER           = 1
    NO_WATER_RND       = 2
    NO_NEXT_LINK       = 3
    NO_NEXT_LINK_WALL  = 4
    NO_ENTRY_LINK      = 5
    STOP_ON_LINK_BREAK = 6
    STOP_ON_CELL_BREAK = 7

    all = { MAX_DEPTH, NO_WATER, NO_WATER_RND, NO_NEXT_LINK, NO_NEXT_LINK_WALL, NO_ENTRY_LINK }

    @classmethod
    def to_str(cls, e:int):
        if e == cls.STILL_RUNNING:      return "STILL_RUNNING"
        if e == cls.MAX_DEPTH:          return "MAX_DEPTH"
        if e == cls.NO_WATER:           return "NO_WATER"
        if e == cls.NO_WATER_RND:       return "NO_WATER_RND"
        if e == cls.NO_NEXT_LINK:       return "NO_NEXT_LINK"
        if e == cls.NO_NEXT_LINK_WALL:  return "NO_NEXT_LINK_WALL"
        if e == cls.NO_ENTRY_LINK:      return "NO_ENTRY_LINK"
        if e == cls.STOP_ON_LINK_BREAK: return "STOP_ON_LINK_BREAK"
        if e == cls.STOP_ON_CELL_BREAK: return "STOP_ON_CELL_BREAK"
        return "none"
        #raise ValueError(f"SIM_EXIT_FLAG: {e} is not in {cls.all}")
    @classmethod
    def from_str(cls, s:str):
        if s == "STILL_RUNNING":        return cls.STILL_RUNNING
        if s == "MAX_DEPTH":            return cls.MAX_DEPTH
        if s == "NO_WATER":             return cls.NO_WATER
        if s == "NO_WATER_RND":         return cls.NO_WATER_RND
        if s == "NO_NEXT_LINK":         return cls.NO_NEXT_LINK
        if s == "NO_NEXT_LINK_WALL":    return cls.NO_NEXT_LINK_WALL
        if s == "NO_ENTRY_LINK":        return cls.NO_ENTRY_LINK
        if s == "STOP_ON_LINK_BREAK":   return cls.STOP_ON_LINK_BREAK
        if s == "STOP_ON_CELL_BREAK":   return cls.STOP_ON_CELL_BREAK
        raise ValueError(f"SIM_EXIT_FLAG: {s} is not in {set(SIM_EXIT_FLAG.to_str(s) for s in cls.all)}")

class SubStepData:
    """ Information per sub step """
    def __init__(self):
        self.currentL             : Link        = None
        self.currentL_deg         : float       = None
        self.currentL_life        : float       = None
        self.currentL_candidates  : list[Link]  = None
        self.currentL_candidatesW : list[float] = None
        self.water_abs            : float       = None
        self.water                : float       = None

class StepData:
    """ Information per step """
    def __init__(self):
        self.subs               : list[SubStepData] = list()
        self.entryL             : Link              = None
        self.entryL_candidates  : list[Link]        = None
        self.entryL_candidatesW : list[float]       = None
        self.exitL              : Link              = None
        self.break_flag         : int               = SIM_EXIT_FLAG.STILL_RUNNING

#-------------------------------------------------------------------

class MW_Sim:
    def __init__(self, cont: MW_Cont, links: MW_Links):
        self.cfg : MW_sim_cfg = cont.root.mw_sim
        self.cont : MW_Cont = cont
        self.links : MW_Links = links

        # empty trace data
        self.step_reset()
        self.step_reset_trace()

    #-------------------------------------------------------------------

    def rnd_store(self):
        #self.rndState = rnd.getstate()
        s = None if self.cfg.debug_rnd.seed_regen else self.cfg.debug_rnd.seed
        self.cfg.debug_rnd.seed = utils.rnd_reset_seed(s)

    def rnd_restore(self):
        # NOTE:: just call some amount of randoms to modify seed, could modify state but requires copying a 600 elemnt tuple
        #rnd.setstate(self.rndState)
        self.cfg.debug_rnd.seed = utils.rnd_reset_seed(self.cfg.debug_rnd.seed, self.cfg.debug_rnd.seed_mod)

    def backup_state(self):
        # delegate backup to the links
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.backupState()

        # store cells state too
        self.cont.backupState()

        # store random too
        self.rnd_store()

    def backup_state_restore(self):
        # restore all
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.backupState_restore()
        self.cont.backupState_restore()
        self.rnd_restore()

        # global recalculation including graphs
        self.links.comps_recalc()

    #-------------------------------------------------------------------

    def reset(self, rnd = False):
        # reset links and cells
        if rnd: self.state_reset_rnd()
        else: self.state_reset()

        self.step_reset()
        self.step_reset_trace()

    def state_reset(self, life=1.0, picks=0):
        # modify links direclty
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            l.reset(life, picks)

        # reset cells
        self.cont.reset()

        # global recalculation including graphs
        self.links.comps_recalc()

    def state_reset_rnd(self, min_val=0, max_val=1, max_picks = 8, max_entry = 8):
        # modify links direclty
        for key in self.links.links_graph.nodes():
            l = self.links.get_link(key)
            r = lambda : rnd.random() * (max_val-min_val) + min_val
            life = r()
            picks = int(r()*max_picks)
            entry = int(r()*self.get_entryProbability(l)*max_entry)
            l.reset(life, picks, entry)

        # reset cells normally
        self.cont.reset()

        # global recalculation including graphs
        self.links.comps_recalc()

    def step_reset(self):
        self.currentL   : Link  = None
        self.prevL      : Link  = None
        self.water      : float = self.cfg.water__start
        self.water_abs  : float = 0

        self.entryL     : Link  = None
        self.exit_flag  : int   = SIM_EXIT_FLAG.STILL_RUNNING
        self.step_path  : list[tuple[neigh_key_t, float]] = []

    def step_reset_trace(self):
        self.step_id = self.step_depth = -1
        self.trace_data : list[StepData] = list()
        self.step_trace : StepData       = None
        self.sub_trace  : SubStepData    = None

    #-------------------------------------------------------------------

    def step_degradeAll(self):
        for l in self.links.internal:
            l.degrade(self.cfg.link_deg)

    def step(self, log_step):
        self.step_reset()
        self.step_id += 1

        # LOG: config/limit logs
        self.logs_cutmsg_disabled_prev = DEV.logs_cutmsg_disabled
        self.log = log_step
        self.log_trace = self.log and self.cfg.debug_log_trace
        log_links_prev = self.links.log
        self.links.log = self.log
        DEV.logs_cutmsg_disabled = True

        # LOG: initial water
        if self.log:
            DEV.log_msg_sep(DEV.logs_cutmsg * 0.75)
            DEV.log_msg(f" > ({self.step_id}) : starting water {self.water}", {"SIM", "STEP"})

        # TRACE: writing the full trace slows down the process, even more when print to console!
        if (self.log_trace):
            self.step_trace = StepData()
            self.trace_data.append(self.step_trace)


        # get entry
        self.get_entryLink()
        if not self.check_start():
            return

        # LOG: entry
        if self.log:
            DEV.log_msg(f" > ({self.step_id}) : {self.currentL}", {"SIM", "ENTRY" })
        # TRACE: log entry
        if self.log_trace:
            DEV.log_msg(f" >>> ENTRY CANDIDATES len({len(self.step_trace.entryL_candidates)})", {"SIM", "ENTRY"})
            for (l,w) in zip(self.step_trace.entryL_candidates, self.step_trace.entryL_candidatesW):
                DEV.log_msg(f"      [{w:.2f}] {l}", {"SIM", "ENTRY", "TRACE"})


        # main loop with a break condition
        self.infiltration_loop()


        # LOG: exit
        if self.log:
            DEV.log_msg(f" >>> ({self.step_id}) : exit {SIM_EXIT_FLAG.to_str(self.exit_flag)} : L ({self.currentL})", {"SIM", "EXIT"})
            DEV.log_msg(f" >>> PATH len({len(self.step_path)})", {"SIM", "PATH"})
            if self.cfg.debug_log_path:
                for i,(k,w) in enumerate(self.step_path):
                    DEV.log_msg(f"      [{i}] {self.links.get_link(k)} - w:{w:.2f}", {"SIM", "PATH"})

        # TRACE: exitL
        if self.cfg.debug_log_trace:
            self.step_trace.exitL = self.currentL

        # LOG: exit cfg
        if self.log:
            DEV.log_msg_sep(DEV.logs_cutmsg * 0.75)
        self.links.log = log_links_prev
        DEV.logs_cutmsg_disabled = self.logs_cutmsg_disabled_prev

    def infiltration_buildPath(self):
        if self.currentL:
            self.step_path.append( (self.currentL.key_cells, self.water) )

    def infiltration_loop(self):
        self.step_depth = -1
        while self.check_continue():
            self.step_depth += 1

            # TRACE: build step
            if (self.cfg.debug_log_trace):
                self.sub_trace = SubStepData()
                self.step_trace.subs.append(self.sub_trace)

            # choose next link to propagate
            self.get_nextLink()

            # apply degradation etc
            if self.currentL:
                self.water_degradation()
                self.link_degradation()

                # TRACE: log step
                if self.log_trace:
                    DEV.log_msg(f" > ({self.step_id},{self.step_depth})"
                                f" : {self.sub_trace.currentL}, n{len(self.sub_trace.currentL_candidates)}"
                                f" - dw({self.sub_trace.water_abs:.3f}) dl({self.sub_trace.currentL_deg:.3f}) : w({self.sub_trace.water:.3f})"
                                #f" : n{len(self.sub_trace.currentL_candidates)} {self.sub_trace.currentL_candidatesW[:32]}"
                                ,{"SIM", "NEXT", "TRACE"})
                    if self.cfg.debug_log_trace_candidates:
                        for (l,w) in zip(self.sub_trace.currentL_candidates, self.sub_trace.currentL_candidatesW):
                            DEV.log_msg(f"      [{w:.2f}] {l}", {"SIM", "NEXT", "TRACE"})

    #-------------------------------------------------------------------
    #  https://docs.python.org/dev/library/random.html#random.choices

    def get_entryLink(self):
        candidates = self.links.external

        # candidates not found
        if not candidates:
            self.entryL = None
            prob_weights = []

        # rnd.choices may fail due to all prob_weights being null etc
        else:
            prob_weights = [ self.get_entryProbability(l) for l in candidates ]
            try:
                picks = rnd.choices(candidates, prob_weights)
                self.entryL = picks[0]
                self.entryL.picks_entry +=1

            except ValueError as e:
                self.entryL = None

        # found an entry
        if self.entryL:
            self.currentL = self.entryL

        self.infiltration_buildPath()

        # TRACE: build entry
        if self.cfg.debug_log_trace:
            self.step_trace.entryL = self.entryL
            self.step_trace.entryL_candidates = candidates
            self.step_trace.entryL_candidatesW = prob_weights

    def get_entryProbability(self, l:Link):
        # link dir align (face normal)
        a = self.get_entryAlign(l.dir)
        p = a

        # weight using face area (normalized)
        if not self.cfg.debug_skip_entry_area:
            p*= l.areaFactor

        return p

    def get_entryAlign(self, vdir:Vector, bothDir=False):
        # relative position water dir
        water_dir_inv = -self.cfg.dir_entry.normalized()
        a = vdir.dot(water_dir_inv)
        if bothDir: a = abs(a)

        # cut-off
        if a < self.cfg.dir_entry_minAlign:
            return 0

        # normalize including potential negative align
        a_norm = (a - self.cfg.dir_entry_minAlign) / (1.0 - self.cfg.dir_entry_minAlign)
        return a_norm

    #-------------------------------------------------------------------

    def get_nextLink(self):
        # merge neighs, the water could scape to the outer surface
        candidates = self.links.get_link_neighs(self.currentL.key_cells)

        ## drop prev from candidates? implicit by gravity direction
        #if self.prevL: candidates -= [self.prevL]

        # candidates not found
        if not candidates:
            self.currentL = None
            prob_weights = []

        # rnd.choices may fail due to all prob_weights being null etc
        else:
            prob_weights = [ self.get_nextProbability(l) for l in candidates ]
            self.prevL = self.currentL
            try:
                picks = rnd.choices(candidates, prob_weights)
                self.currentL = picks[0]
                self.currentL.picks += 1

            except ValueError as e:
                self.currentL = None

        self.infiltration_buildPath()

        # TRACE: build next
        if self.cfg.debug_log_trace:
            self.sub_trace.currentL = self.currentL
            self.sub_trace.currentL_candidates = candidates
            self.sub_trace.currentL_candidatesW = prob_weights

    def get_nextProbability(self, l:Link):
        # links hanging in the air are not valid
        #if self.links.solid_link_check(l):
        #    return 0

        # relative pos align
        dpos = l.pos - self.currentL.pos
        a = self.get_nextAlign(dpos.normalized())
        p = a

        # weight by link resistance field
        if l.state == LINK_STATE_ENUM.SOLID:
            r = self.link_resistance(l)
            if not self.cfg.debug_skip_next_maxResist:
                r = min(r, 0.999)
            p *= 1-r

        return p

    def get_nextAlign(self, vdir:Vector, bothDir=False):
        # relative pos align
        water_dir_inv = self.cfg.dir_next.normalized()
        a = vdir.normalized().dot(water_dir_inv)
        if bothDir: a = abs(a)

        # cut-off
        if a < self.cfg.dir_next_minAlign:
            return 0

        # normalize including potential negative align
        a_norm = (a - self.cfg.dir_next_minAlign) / (1.0 - self.cfg.dir_next_minAlign)
        return a_norm

    #-------------------------------------------------------------------

    def link_resistance(self, l:Link):
        # dead link opposes no resistance
        r = l.life

        # mod by the resistance field at its center
        r *= l.resistance * self.cfg.link_resist_weight

        ## also consider area factor so area size affects the resistance opposed?
        #if self.cfg.debug_skip_next_area:
        #    r *= l.areaFactor
        return r

    def link_degradation(self):
        d = -1
        if self.currentL.state == LINK_STATE_ENUM.SOLID:

            # degradation depends on water abs but distributed over the link surface (cancels out area)
            d = self.water_abs * self.cfg.link_deg / self.currentL.areaFactor

            # apply degradation -> potential break
            self.currentL.degrade(d)

            if self.link_rnd_break_event():
                self.currentL.life = -1

            if self.currentL.life <= 0:
                DEV.log_msg(f" *** ({self.step_id}) : link_break_event {self.currentL}", {"SIM", "EVENT"})
                breaking = self.links.setState_link_check(self.currentL.key_cells, LINK_STATE_ENUM.AIR)

                # stop simulation on break
                if self.cfg.step_stopBreak:
                    if "LINK" in self.cfg.step_stopBreak_event:
                        self.exit_flag = SIM_EXIT_FLAG.STOP_ON_LINK_BREAK
                    elif "CELL" in self.cfg.step_stopBreak_event:
                        if breaking:
                            self.exit_flag = SIM_EXIT_FLAG.STOP_ON_CELL_BREAK

        # TRACE: link deg
        if self.cfg.debug_log_trace:
            self.sub_trace.currentL_deg = d
            self.sub_trace.currentL_life = self.currentL.life

    def link_rnd_break_event(self):
        if self.currentL.life < self.cfg.link_rnd_break_minCheck:
            minLife = self.currentL.life / self.cfg.link_rnd_break_minCheck
            if minLife * self.cfg.link_rnd_break_resistProb < rnd.random():
                DEV.log_msg(f" *** ({self.step_id}) : link_rnd_break_event L{self.currentL}", {"SIM", "EVENT"})
                return True
        return False

    def water_degradation(self):
        # check potential full water absorption
        if not self.water_rnd_abs_event():

            # minimun abs that happens when the water runs through a exterior face or an eroded interior one
            if self.currentL.state != LINK_STATE_ENUM.SOLID:
                wa = self.cfg.water_abs_air * self.currentL.areaFactor
                w = wa

            # interior solid abs takes into account resistance too
            else:
                wr = self.link_resistance(self.currentL) * self.cfg.water_deg
                wa = self.cfg.water_abs_solid * self.currentL.areaFactor
                w = wa + wr

            # abs water
            self.water -= w
            if self.water > 0:
                self.water_abs = w
            else:
                self.water_abs = w + self.water

        # TRACE: water abs
        if self.cfg.debug_log_trace:
            self.sub_trace.water_abs = self.water_abs
            self.sub_trace.water = self.water

    def water_rnd_abs_event(self):
        if self.water < self.cfg.water_rnd_abs_minCheck:
            minAbsorb = self.water / self.cfg.water_rnd_abs_minCheck
            if minAbsorb * self.cfg.water_rnd_abs_continueProb < rnd.random():
                self.exit_flag = SIM_EXIT_FLAG.NO_WATER_RND
                DEV.log_msg(f" *** ({self.step_id}) : water_rnd_abs_event w:{self.water}", {"SIM", "EVENT"})

                # consider how much water was abs
                self.water_abs = self.cfg.water_rnd_abs_damage * self.water
                self.water -= self.water_abs
                return True

        return False

    #-------------------------------------------------------------------

    def check_start(self):
        # no entry link was found
        if not self.entryL:
            self.exit_flag = SIM_EXIT_FLAG.NO_ENTRY_LINK

        return self.check_exit_flag()

    def check_continue(self):
        if self.exit_flag == SIM_EXIT_FLAG.STILL_RUNNING:

            # no next link was found
            if not self.currentL:
                if self.prevL.state == LINK_STATE_ENUM.WALL: self.exit_flag = SIM_EXIT_FLAG.NO_NEXT_LINK_WALL
                else: self.exit_flag = SIM_EXIT_FLAG.NO_NEXT_LINK

            # no more water
            elif self.water < 0:
                self.exit_flag = SIM_EXIT_FLAG.NO_WATER

            # max iterations when enabled
            elif self.cfg.step_maxDepth != -1 and self.step_depth >= self.cfg.step_maxDepth-1:
                self.exit_flag = SIM_EXIT_FLAG.MAX_DEPTH

        # the flag could be potentially set at other steps: link break, water rnd abs...
        return self.check_exit_flag()

    def check_exit_flag(self):
        # found msg means exit condition was met
        if self.exit_flag != SIM_EXIT_FLAG.STILL_RUNNING:
            # TRACE: keep msg per trace
            if self.cfg.debug_log_trace:
                self.step_trace.break_flag = self.exit_flag
            return False

        # continue sim when no exit msg recorded
        return True