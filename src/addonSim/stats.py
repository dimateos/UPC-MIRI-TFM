# SPDX-License-Identifier: GPL-2.0-or-later
# ref: ant_landscape addon
# Probably too much logic during the trace logging but ok

from time import time

import psutil


try:
    import psutil
    #print('psutil available')
    psutil_available = True
except ImportError:
    psutil_available = False


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


    def log(self):
        t = self.time()
        dt = self.time_diff()
        print(f"{self.name}//\t t:{t:>10.6f}   dt:{dt:>10.6f}")

    def log_mem(self):
        m = self.memory_max()
        lm = self.memory_last()
        dm = self.diffmem
        print(f"\t m:{m:>10}   lm:{lm:>10}   dm:{dm:>10}")

    def log_full(self):
        self.log()
        self.log_mem()


def testStats():
    # sample operations
    import numpy as np

    stats = Stats()
    stats.log_full()

    a = np.zeros(10000000)
    print("\n>> a = np.zeros(10000000)")
    stats.log_full()

    a = np.sin(a)
    print("\n>> a = np.sin(a)")
    stats.log_full()

    a = np.cos(a)
    print("\n>> a = np.cos(a)")
    stats.log_full()

    a = np.cos(a) ** 2 + np.sin(a) ** 2
    print("\n>> a = np.cos(a) ** 2 + np.sin(a) ** 2")
    stats.log_full()