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


# -------------------------------------------------------------------

class Stats:
    def __init__(self, name="Stats"):
        self.name = name
        self.memstats_available = False
        if psutil_available:
            self.process = psutil.Process()
            self.memstats_available = True
        self.reset()

    def reset(self):
        self.lasttime = self._gettime()
        self.firsttime = self.lasttime
        self.basemem = self._getmem()
        self.maxmem = self.lastmem = self.diffmem = 0
        self.elapsedtime = 0


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

# -------------------------------------------------------------------

    def logMsg(self, msg):
       print(f"{self.name}//                              - {msg}")

    def logDt(self, msg: str = " "):
        if not DEV.logs_stats: return
        t = self.time()
        dt = self.time_diff()

        #if msg: print(f"{self.name}//  {msg}")
        #print(f"\t t:{t:>10.6f}   dt:{dt:>10.6f}")
        if msg: print(f"{self.name}// dt:{dt:>10.6f}s ({t:>10.6f}s) - {msg}")

    def logT(self, msg: str = " "):
        if not DEV.logs_stats: return
        t = self.time()
        if msg: print(f"{self.name}// total time:    ({t:>10.6f}s) - {msg}")

    # OPT:: single line or something like log
    def logMem(self, msg: str = " "):
        if not DEV.logs_stats: return
        m = self.memory_max()
        lm = self.memory_last()
        dm = self.diffmem

        if msg: print(f"{self.name}// {msg}")
        print(f"\t m:{m:>10}   lm:{lm:>10}   dm:{dm:>10}")

    def logFull(self, msg: str = " "):
        self.log(msg)
        self.logMem("")

# -------------------------------------------------------------------

gStats = None
def getStats() -> Stats:
    """ Globally shared stats """
    global gStats
    if gStats is None:
        gStats = Stats()
    return gStats


def testStats(log = False):
    # sample operations
    import numpy as np
    stats = getStats()
    stats.logFull()

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