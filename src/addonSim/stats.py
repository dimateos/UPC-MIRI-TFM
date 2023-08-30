# SPDX-License-Identifier: GPL-2.0-or-later
# ref: ant_landscape addon
# OPT:: Probably too much logic during the trace logging but ok e.g. checking psutil and its version

from time import time

try:
    import psutil
    #print('psutil available')
    psutil_available = True
except ImportError:
    psutil_available = False

from .utils_dev import DEV


#-------------------------------------------------------------------

class Stats:
    def __init__(self, name="Stats"):
        self.name = name
        self.memstats_available = False
        if psutil_available:
            self.process = psutil.Process()
            self.memstats_available = True
        self.reset(False)

    def reset(self, log= True):
        self.lasttime = self._gettime()
        self.firsttime = self.lasttime
        self.basemem = self._getmem()
        self.maxmem = self.lastmem = self.diffmem = 0
        self.elapsedtime = 0
        if log: self.logMsg(f"reset... (base mem: {self.basemem})")

    def _gettime(self):
        """return the time in seconds used by the current process."""
        if psutil_available:
            """ Handle psutil API change. """
            if hasattr(self.process, "get_cpu_times"):
                m = self.process.get_cpu_times()
            else:
                m = self.process.cpu_times()
            return m.user + m.system
        return time()

    def _getmem(self):
        """return the resident set size in bytes used by the current process."""
        if psutil_available:
            """ Handle psutil API change. """
            if hasattr(self.process, "get_memory_info"):
                m = self.process.get_memory_info()
            else:
                m = self.process.memory_info()
            return m.rss
        return 0


    def time_diff(self):
        """return the time since the LAST call in seconds used by the current process."""
        old = self.lasttime
        self.lasttime = self._gettime()
        self.elapsedtime = self.lasttime - old
        return self.elapsedtime

    def time(self):
        """return the time since the FIRST call in seconds used by the current process."""
        t = self._gettime()
        return t - self.firsttime

    def memory_max(self):
        """return the maximum resident mem size since the FIRST call in bytes used by the current process."""
        m = self._getmem()
        d = m - self.basemem
        if d > self.maxmem:
            self.maxmem = d
        return self.maxmem

    def memory_last(self):
        """return the CURRENT mem size call in bytes used by the current process."""
        m = self._getmem()
        d = m - self.basemem
        self.diffmem = d - self.lastmem
        self.lastmem = d
        return d

    #-------------------------------------------------------------------

    logType = { "STATS" }

    def logMsg(self, msg, uncut=False):
        msgStart = f"{self.name}//"
        DEV.log_msg(msg, Stats.logType, msgStart, DEV.logs_stats_sep, cut=not uncut)

    def logDt(self, msg: str = "", uncut=False):
        if not DEV.logs_stats_dt: return
        t = self.time()
        dt = self.time_diff()

        msgStart = f"{self.name}// dt:{dt:>10.6f}s ({t:>10.6f}s)"
        DEV.log_msg(msg, Stats.logType, msgStart, DEV.logs_stats_sep, cut=not uncut)

    def logT(self, msg: str = "", uncut=False):
        if not DEV.logs_stats_dt: return
        t = self.time()

        msgStart = f"{self.name}// total time:    ({t:>10.6f}s)"
        DEV.log_msg(msg, Stats.logType, msgStart, DEV.logs_stats_sep, cut=not uncut)

    # OPT:: single line or something like log
    def logMem(self, msg: str = "", uncut=False):
        if not DEV.logs_stats_dt: return
        m = self.memory_max()
        lm = self.memory_last()
        dm = self.diffmem

        msgStart = f"{self.name}// dm:{dm:>9}   ({m:>10}b)"
        DEV.log_msg(msg, Stats.logType, msgStart, DEV.logs_stats_sep, cut=not uncut)

    def logFull(self, msg: str = "", uncut=False):
        if not DEV.logs_stats_total: return
        tmp = DEV.logs_stats_dt
        DEV.logs_stats_dt = DEV.logs_stats_total

        self.logT(msg, uncut=uncut)
        self.logMem("", uncut=uncut)
        DEV.logs_stats_dt = tmp


#-------------------------------------------------------------------

gStats = None
def getStats() -> Stats:
    """ Globally shared stats """
    global gStats
    if gStats is None:
        gStats = Stats()
    return gStats

def testStats(new= True, log= True):
    # sample operations
    import numpy as np
    stats = Stats() if new else getStats()
    stats.reset()

    a = np.zeros(10000000)
    if log:
        print("\n>> a = np.zeros(10000000)")
        stats.logFull()

    a = np.sin(a)
    if log:
        print("\n>> a = np.sin(a)")
        stats.logFull()

    a = np.cos(a)
    if log:
        print("\n>> a = np.cos(a)")
        stats.logFull()

    a = np.cos(a) ** 2 + np.sin(a) ** 2
    if log:
        print("\n>> a = np.cos(a) ** 2 + np.sin(a) ** 2")
        stats.logFull()


#-------------------------------------------------------------------

def timeit(flambda, n=1000, msg: str = ""):
    import timeit
    t = timeit.timeit(flambda, number=n)
    log = f"Timed// total time:    ({t:>10.6f}s)"
    if msg: log += f" - {msg}"
    print(log)
