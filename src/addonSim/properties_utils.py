import bpy
import bpy.types as types
import bpy.props as props

from .utils_dev import DEV


# NOTE:: foldable ui sections should use some kind of id global storage like IMGUI frameworks, using a predefined blender prop is SO cumbersome...
#-------------------------------------------------------------------

class RND_config(types.PropertyGroup):
    """ Common config for random number generation """

    seed: props.IntProperty(
        name="RND seed", description="Seed the random generator, -1 to unseed it",
        default=64, min=-1,
    )
    seed_mod: props.IntProperty(
        name="RND seed mod", description="Modify the current random generator",
        default=0, min=0, max=100,
    )
    seed_regen: props.BoolProperty(
        name="RND seed gen new", description="Use a new random seed per OP call",
        default=not DEV.FORCE_NO_RND,
    )

class Prop_inspector(types.PropertyGroup):
    """ Meta filters to display/edit a property group in a panel """

    # utility to avoid additional operator refreshes, set manually back to False after skip
    meta_show_toggled: props.BoolProperty(
        description="Meta flag to indicate no config change",
        default=False,
    )

    def set_meta_show_toggled(self, context):
        self.meta_show_toggled = True
    def reset_meta_show_toggled(self):
        self.meta_show_toggled = False

    def skip_meta_show_toggled(self):
        if self.meta_show_toggled:
            self.meta_show_toggled = False
            return True
        return False

    #-------------------------------------------------------------------

    # main toggle to fold the property inspector
    meta_show_props: props.BoolProperty(
        # NOTE:: text name to be replaced in the ui
        description="Show properties",
        default=False,
        update=set_meta_show_toggled
    )

    # options for interacting with the props
    meta_propFilter: props.StringProperty(
        name="Filter id", description="Separate values with commas, start with `-` for a excluding filter.",
        default="-meta",
    )
    meta_propDefault: props.BoolProperty(
        name="default", description="Include default unchanged props",
        default=True,
    )
    meta_propEdit: props.BoolProperty(
        name="edit", description="Enable editting the props",
        default=False,
    )
    meta_propShowId: props.BoolProperty(
        name="id", description="Show property id or its name",
        default=True,
    )

    # group foldable sections with "debug" as part of its name
    meta_show_debug_props: props.BoolProperty(
        name="debug...", description="Show debug properties",
        default=False,
        update=set_meta_show_toggled
    )

    # additional toggles in the menus, no description and name set outside
    meta_show_1: props.BoolProperty(
        default=False,
        update=set_meta_show_toggled
    )
    meta_show_2: props.BoolProperty(
        default=False,
        update=set_meta_show_toggled
    )
    meta_show_3: props.BoolProperty(
        default=False,
        update=set_meta_show_toggled
    )

#-------------------------------------------------------------------

class CONST_FILTERS:
    filter_readOnly = [
        "__",              # python meta
        "bl_", "rna_",     # blender meta
    ]
    """ Avoid doc attrs and read-only RNA types, no need to trim or lowercase etc """

    filterExact_readOnly = [
        "name",            # blender adds name to everything?
        "layout",          # preferences panel adds an implicit layout
    ]
    """ More blender props with a short full name """

    filter_nonBlProp = [
        "nbl_"             # mw meta non props
    ]
    """ Properties that cant be rendered in the ui direclty with ui.prop(data, name) """

    filter_debug = [
        "debug"
    ]
    """ Group debug properties apart """

def getFilters_split(propFilter):
    if propFilter:
        propFilter_clean = propFilter.replace(" ","").lower()
        filters =  [ f for f in propFilter_clean.split(",") if f]
        filters_inc = [f for f in filters if f[0]!="-"]
        filters_exc = [f[1:] for f in filters if f[0]=="-"]
        return filters_inc, filters_exc
    return [],[]

def skipFilters(name, filters_inc, filters_exc):
    # apply excluding/including filter on clean name
    name_clean = name.strip().lower()
    if (filters_inc):
        mask_inc = [ f in name_clean for f in filters_inc ]
        if not any(mask_inc): return True
    if (filters_exc):
        mask_exc = [ f in name_clean for f in filters_exc ]
        if any(mask_exc): return True
    return False

#-------------------------------------------------------------------

def getProps_names(data, addDefault=True, exc_nonBlProp=True, groupsInstead = False):
    """ Get all properties names of an object, e.g. not just the modified ones in PropertyGroup.keys()
        # NOTE:: skip read only prop groups
    """
    props_names = []

    data_dir = dir(data) if addDefault else data.keys()
    for prop_name in data_dir:
        # skip prop groups and callable methods (sub classes are class props, not instance)
        prop_ref = getattr(data, prop_name)
        if callable(prop_ref): continue

        # work with groups or props
        isGroup = isinstance(prop_ref, types.PropertyGroup)
        if (isGroup and not groupsInstead) or (not isGroup and groupsInstead): continue

        # ignore non bl props
        if exc_nonBlProp:
            mask_nbl = [ prop_name.startswith(f) for f in CONST_FILTERS.filter_nonBlProp]
            if any(mask_nbl): continue

        # ignore read only props
        filterMask = [ prop_name.startswith(f) for f in CONST_FILTERS.filter_readOnly]
        if any(filterMask): continue
        filterMask = [ prop_name == f for f in CONST_FILTERS.filterExact_readOnly]
        if any(filterMask): continue

        props_names.append(prop_name)
    return props_names

def getProps_namesFiltered(data, propFilter:str=None, addDefault=True, exc_nonBlProp=True):
    """ Get all properties names filtered """
    filters_inc, filters_exc = getFilters_split(propFilter)
    prop_namesFiltered = []

    # iterate the props
    prop_names = getProps_names(data, addDefault, exc_nonBlProp)
    for prop_name in prop_names:

        # filter by prop name
        if skipFilters(prop_name, filters_inc, filters_exc):
            continue

        prop_namesFiltered.append(prop_name)
    return prop_namesFiltered

def getProps_groups(data, groupFilter:str=None):
    """ Excluded from getProp_names """
    filters_inc, filters_exc = getFilters_split(groupFilter)
    group_names = []

    # iterate groups
    prop_names = getProps_names(data, groupsInstead=True)
    for prop_name in prop_names:

        # filter group name
        if skipFilters(prop_name, filters_inc, filters_exc): continue

        group_names.append(prop_name)
    return group_names

def getProps_splitDebug(prop_namesFiltered):
    prop_names = []
    debug_names = []
    for prop_name in prop_namesFiltered:

        # apply excluding/including filter on clean name
        prop_name_clean = prop_name.strip().lower()
        mask_debug = [ f in prop_name_clean for f in CONST_FILTERS.filter_debug ]

        if not any(mask_debug):
            prop_names.append(prop_name)
        else:
            debug_names.append(prop_name)

    return prop_names, debug_names

#-------------------------------------------------------------------

def copyProps(src, dest, propFilter:str=None, addDefault=True, exc_nonBlProp=True):
    """ Copy all props of an object, e.g. potentially not just the modified ones in PropertyGroup.keys()
        # The whole property is read-only but its values can be modified, avoid writing it one by one...
    """
    if propFilter:
        props_names = getProps_namesFiltered(src, propFilter, addDefault, exc_nonBlProp)
    else:
        props_names = getProps_names(src, addDefault, exc_nonBlProp)

    for prop_name in props_names:
        setattr(dest, prop_name, getattr(src, prop_name))

def copyProps_groups(src, dest, propFilter:str=None, groupFilter:str=None, addDefault=True, exc_nonBlProp=True):
    """ Copy filtered properties of filtered inner groups """
    group_names = getProps_groups(src, groupFilter)
    for group_name in group_names:
        copyProps_groups_rec(getattr(src, group_name), getattr(dest, group_name), propFilter, addDefault, exc_nonBlProp)

def copyProps_groups_rec(src, dest, propFilter:str=None, groupFilter:str=None, addDefault=True, exc_nonBlProp=True, recFilter = False):
    """ Copy all properties recursive, no inner filter """
    copyProps(src, dest, propFilter, addDefault, exc_nonBlProp)
    # groups dont show up normally
    group_names = getProps_groups(src, groupFilter)
    for group_name in group_names:
        filter = groupFilter if recFilter else ""
        copyProps_groups_rec(getattr(src, group_name), getattr(dest, group_name), propFilter, filter, addDefault, exc_nonBlProp, recFilter)

#-------------------------------------------------------------------

def resetProps(src, propFilter:str=None):
    """ Reset filtered properties without touching inner groups """
    prop_names = getProps_namesFiltered(src, propFilter)
    for prop_name in prop_names:
        src.property_unset(prop_name)

def resetProps_groups(src, propFilter:str=None, groupFilter:str=None):
    """ Reset filtered properties of filtered inner groups """
    group_names = getProps_groups(src, groupFilter)
    for group_name in group_names:
        resetProps_rec(getattr(src, group_name), propFilter)

def resetProps_rec(src, propFilter:str=None, groupFilter:str=None, recFilter = False):
    """ Reset all properties recursive, no inner filter """
    resetProps(src, propFilter)
    # groups dont show up normally
    group_names = getProps_groups(src, groupFilter)
    for group_name in group_names:
        filter = groupFilter if recFilter else ""
        resetProps_rec(getattr(src, group_name), propFilter, filter, recFilter)