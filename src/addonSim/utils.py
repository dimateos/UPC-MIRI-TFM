# misc utils
#-------------------------------------------------------------------

def get_timestamp() -> int:
    """ Get current timestamp as int """
    from datetime import datetime
    tim = datetime.now()
    return tim.hour*10000+tim.minute*100+tim.second

def debug_rnd_seed(s: int = None) -> int:
    """ Persists across separate module imports, return the seed to store in the config """
    import mathutils.noise as bl_rnd
    import random as rnd

    if s is None or s < 0:
        s = get_timestamp()

    rnd.seed(s)
    bl_rnd.seed_set(s)
    return s

def rnd_string(length=16):
    """Generates a random string of specified length"""
    import string
    import random as rnd
    letters = string.ascii_letters
    return ''.join(rnd.choice(letters) for _ in range(length))

_uuidxLast = -1
def get_uuidx():
    global _uuidxLast
    _uuidxLast +=1
    return _uuidxLast

# OPT:: test perf, it might be very bad? timeit(lambda: dict(**get_kwargs()))
def get_kwargs(startKey_index = 0):
    from inspect import currentframe, getargvalues
    frame = currentframe().f_back
    keys, _, _, values = getargvalues(frame)
    kwargs = {}
    for key in keys[startKey_index:]:
        if key != 'self':
            kwargs[key] = values[key]
    return kwargs

def get_filtered(listFull:list, filter:str):
    listFiltered = []

    filters = filter.split(",")
    for f in filters:
        f = f.strip()

        # range filter
        if "_" in f:
            i1,i2 = f.split("_")
            listFiltered += listFull[int(i1):int(i2)]
        # specific item
        else:
            try: listFiltered.append(listFull[int(f)])
            except IndexError: pass

    return listFiltered

def assure_list(val_list):
    if not isinstance(val_list, list):
        return [val_list]
    return val_list

def compare_dicts(dict1, dict2):
    if set(dict1.keys()) != set(dict2.keys()):
        return False
    for key in dict1:
        if dict1[key] != dict2[key]:
            return False
    return True

def listMap_dict(d):
    l = [None] * len(d)
    for k,val in d.items():
        l[k] = val
    return l

def vec3_to_string(v, fmt:str = ".2f"):
    fmt_vec = f"({{:{fmt}}},{{:{fmt}}},{{:{fmt}}})"
    return f"{fmt_vec}".format(*v)

def key_to_string(k:tuple[int,int], fmt:str = ">2"):
    fmt_vec = f"({{:{fmt}}},{{:{fmt}}})"
    return f"{fmt_vec}".format(*k)

def clamp(value, min_val=0, max_val=1):
    return max(min(value, max_val), min_val)

def clamp_inplace(value_seq, min_val=0, max_val=1):
    """ Clapm values in place, any size """
    for i in range(len(value_seq)):
        value_seq[i] = clamp(value_seq[i], min_val, max_val)

    # return tho in place in case it was used before assigning
    return value_seq