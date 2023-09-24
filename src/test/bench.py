
import importlib
#-------------------------------------------------------------------

from addonSim import utils
importlib.reload(utils)
from addonSim import utils_geo
importlib.reload(utils_geo)

def bench_meshMaps(stats, me):
    stats.reset()

    # query mesh props
    utils_geo.queryLogAll_mesh(me)
    stats.logFull("bench_meshMaps")
    print()
    nRep = 2
    n = 50
    delete = False

    ret1, ret2, ret3 = None, None, None
    for i in range(nRep):
        print()
        print(f"rep {i}")

        t = """ maps dict based """
        stats.reset()
        for n in range(n):
            ret1 = utils_geo.map_VtoF_EtoF_VtoE_dictBased(me)
        stats.logFull(t)
        if delete: del ret1

        t = """ maps general method """
        stats.reset()
        query = { "VtoF": True, "EtoF": True, "VtoE": True }
        for n in range(n):
            ret3 = utils_geo.get_meshDicts(me, queries_dict=query, queries_default=False)
        stats.logFull(t)
        if delete: del ret3

        t = """ maps pre-alloc list based """
        stats.reset()
        for n in range(n):
            ret2 = utils_geo.map_VtoF_EtoF_VtoE(me)
        stats.logFull(t)
        if delete: del ret2


    if not delete:
        t = """ assert equal results"""
        stats.reset()
        assert(ret2[0] == utils.listMap_dict(ret1[0]))
        assert(ret2[1] == utils.listMap_dict(ret1[1]))
        assert(ret2[2] == utils.listMap_dict(ret1[2]))
        assert(ret2[0] == ret3["VtoF"])
        assert(ret2[1] == ret3["EtoF"])
        assert(ret2[2] == ret3["VtoE"])
        stats.logFull(t)
    pass

def bench_meshMaps_FtoF(stats, me):
    stats.reset()

    # query mesh props
    utils_geo.queryLogAll_mesh(me)
    stats.logFull("bench_meshMaps_FtoF")
    print()
    nRep = 2
    n = 50
    delete = False

    ret1, ret2 = None, None
    for i in range(nRep):
        print()
        print(f"rep {i}")

        t = """ maps general method """
        stats.reset()
        query = { "FtoF": True }
        for n in range(n):
            ret1 = utils_geo.get_meshDicts(me, queries_dict=query, queries_default=False)
        stats.logFull(t)
        if delete: del ret1

        t = """ maps specific method """
        stats.reset()
        for n in range(n):
            ret2 = utils_geo.map_FtoF(me)
        stats.logFull(t)
        if delete: del ret2

    if not delete:
        t = """ assert equal results"""
        stats.reset()
        assert(ret1["FtoF"] == ret2)
        stats.logFull(t)
    pass