# Avoiding circular imports around properties and preferences management
#-------------------------------------------------------------------

class CONST_CFG:
    filter_readOnly = [
        "__",              # python meta
        "bl_", "rna_",     # blender meta
    ]
    """ Avoid doc attrs and read-only RNA types, no need to trim or lowercase etc """

    filter_nonBlProp = [
        "nbl_"             # mw meta non props
    ]
    """ Properties that cant be rendered in the ui direclty with ui.prop(data, name) """


def getProps_names(data):
    """ Get all properties names of an object, e.g. not just the modified ones in PropertyGroup.keys() """
    props_names = []
    for prop_name in dir(data):
        # skip callable methods (sub classes are class props, not instance)
        if callable(getattr(data, prop_name)): continue

        # minumun filter of read only props
        filterMask = [ prop_name.startswith(f) for f in CONST_CFG.filter_readOnly]
        if any(filterMask): continue

        props_names.append(prop_name)
    return props_names

def getProps_namesFiltered(data, propFilter:str, exc_nonBlProp=False):
    """ Get all properties names filtered """
    # build dynamic filter prop
    prop_names = getProps_names(data)
    if propFilter:
        propFilter_clean = propFilter.replace(" ","").lower()
        filters =  [ f for f in propFilter_clean.split(",") if f]
        filters_inc = [f for f in filters if f[0]!="-"]
        filters_exc = [f[1:] for f in filters if f[0]=="-"]
    else:
        filters_inc = filters_exc = []

    # iterate the props and check agains all filters
    prop_namesFiltered = []
    for prop_name in prop_names:
        # ignore non bl props
        if exc_nonBlProp:
            mask_nbl = [ prop_name.startswith(f) for f in CONST_CFG.filter_nonBlProp]
            if any(mask_nbl): continue

        # apply excluding/including filter on clean name
        prop_name_clean = prop_name.strip().lower()
        if (filters_inc):
            mask_inc = [ f in prop_name_clean for f in filters_inc ]
            if not any(mask_inc): continue
        if (filters_exc):
            mask_exc = [ f in prop_name_clean for f in filters_exc ]
            if any(mask_exc): continue

        prop_namesFiltered.append(prop_name)
    return prop_namesFiltered

def copyProps(src, dest):
    """ Copy all props of an object, e.g. not just the modified ones in PropertyGroup.keys() """
    # The whole property is read-only but its values can be modified, avoid writing it one by one...
    props_names = getProps_names(src)
    for prop_name in props_names:
        setattr(dest, prop_name, getattr(src, prop_name))
