import bpy
import bpy.types as types

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)
from .properties_utils import Prop_inspector, getProps_namesFiltered, getProps_splitDebug

from .utils_dev import DEV

class CONST_ICONS:
    section_closed = "RIGHTARROW"       # "RIGHTARROW" "DISCLOSURE_TRI_RIGHT"
    section_opened = "DOWNARROW_HLT"    # "DOWNARROW_HLT" "DISCLOSURE_TRI_DOWN"

#-------------------------------------------------------------------

def draw_toggleBox(metadata, propToggle_name:str, layout: types.UILayout, text:str=None) -> tuple[bool, types.UILayout]:
    """ Create a box with a toggle. Return the state of the toggle and the created layout """
    box = layout.box()
    open = getattr(metadata, propToggle_name)
    icon = CONST_ICONS.section_opened if open else CONST_ICONS.section_closed

    if text:
        box.prop(metadata, propToggle_name, toggle=True, icon=icon, text=text)
    else:
        box.prop(metadata, propToggle_name, toggle=True, icon=icon)
    return open, box

def draw_props_raw(data, prop_names:list[str], layout: types.UILayout, showId=False):
    """ Draw a list of object properties in a sub layout. """
    for prop_name in prop_names:
        if showId: layout.row().prop(data, prop_name, text=prop_name)
        else: layout.row().prop(data, prop_name)

#-------------------------------------------------------------------

def draw_props(data, propFilter:str, layout: types.UILayout, showId=False, showDefault=True):
    """ Query and draw all properties of an object in a sub layout. """
    # get the props filtered without the non prop ones
    prop_names = getProps_namesFiltered(data, propFilter, exc_nonBlProp=True, showDefault=showDefault)
    draw_props_raw(data, prop_names, layout, showId)

def draw_propsToggle(data, data_inspector:Prop_inspector, layout:types.UILayout, text:str="Properties") -> tuple[bool, types.UILayout]:
    """ Draw all properties of an object under a toggleable layout. """

    # outer fold
    open, box = draw_toggleBox(data_inspector, "meta_show_props", layout, text)
    if open:

        # top of filter
        split = box.split(factor=0.0)
        split.scale_y = 0.8
        split.prop(data_inspector, "meta_propShowId")
        split.prop(data_inspector, "meta_propDefault")
        split.prop(data_inspector, "meta_propEdit")
        showDefault = getattr(data_inspector, "meta_propDefault")
        showId = getattr(data_inspector, "meta_propShowId")
        editable = getattr(data_inspector, "meta_propEdit")
        propFilter = getattr(data_inspector, "meta_propFilter")

        # filter props
        box.prop(data_inspector, "meta_propFilter", text="")
        prop_names = getProps_namesFiltered(data, propFilter, exc_nonBlProp=True, showDefault=showDefault)

        # split debug props
        splitDebug = getattr(data_inspector, "meta_show_debug_split")
        if splitDebug:
            prop_names, debug_names = getProps_splitDebug(prop_names)
        else:
            debug_names = None

        if (debug_names):
            # debug inner fold
            open_debug, box_debug = draw_toggleBox(data_inspector, "meta_show_debug_props", box)
            if open_debug:
                col = box_debug.column()
                col.enabled = editable
                draw_props_raw(data, debug_names, col, showId)

        # draw the list of props
        col         = box.column()
        col.enabled = editable
        draw_props_raw(data, prop_names, col, showId)

    return open, box

def draw_propsToggle_custom(data, data_inspector:Prop_inspector, layout:types.UILayout, text:str="Properties",
                            propFilter="", showDefault=True, showId=False, editable=True) -> tuple[bool, types.UILayout]:
    """ Draw some properties of an object under a custom toggleable layout. """

    # outer fold
    open, box = draw_toggleBox(data_inspector, "meta_show_props", layout, text)
    if open:
        prop_names = getProps_namesFiltered(data, propFilter, exc_nonBlProp=True, showDefault=showDefault)
        col         = box.column()
        col.enabled = editable
        draw_props_raw(data, prop_names, col, showId)

    return open, box

#-------------------------------------------------------------------

def draw_refresh(data, layout: types.UILayout):
    row = layout.box().row()
    row.scale_y = 1.5
    split = row.split(factor=0.75)
    split.prop(data, "meta_auto_refresh", toggle=True, icon_only=False, icon='FILE_REFRESH')
    split.prop(data, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

#-------------------------------------------------------------------
# OPT:: not reused ui so should go to the op?

def draw_gen_cfg(cfg: MW_gen_cfg, layout: types.UILayout, context: types.Context):
    box = layout.box()
    col = box.column()

    factor = 0.4
    rowsub = col.row().split(factor=factor)
    rowsub.alignment = "LEFT"
    rowsub.label(text="Point Source:")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.struct_nameOriginal)

    rowsub = col.row().split(factor=factor)
    rowsub.alignment = "LEFT"
    rowsub.prop(cfg, "struct_namePrefix")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.get_struct_name())

    rowsub = col.row()
    rowsub.prop(cfg, "source")

    rowsub = col.row()
    rowsub.prop(cfg, "source_limit")
    # IDEA:: show current num found? could do 1 frame delayed stored somewhere
    rowsub = col.row()
    rowsub.prop(cfg, "source_noise")
    rowsub.prop(cfg, "rnd_seed")

    # OPT:: limit avaialble e.g. show convex when available
    box = layout.box()
    col = box.column()
    col.label(text="Generation:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "shape_useConvexHull")
    rowsub.prop(cfg, "shape_useWalls")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "margin_box_bounds")
    rowsub.prop(cfg, "margin_face_bounds")

    draw_gen_cfgDebug(cfg, layout)

    box = layout.box()
    col = box.column()
    col.label(text="Prefs:  (edit in addon panel)")
    prefs = getPrefs()
    col.enabled = False
    col.prop(prefs, "gen_calc_precisionWalls")
    col.prop(prefs, "gen_setup_invertShardNormals")


def draw_gen_cfgDebug(cfg: MW_gen_cfg, layout: types.UILayout):
    # OPT:: not all debug etc... sensible ui in the end

    # Careful with circular deps
    from .preferences import getPrefs
    prefs = getPrefs()

    open, box = draw_toggleBox(prefs.gen_PT_meta_inspector, "meta_show_debug_props", layout)
    if open:
        col = box.column()
        col.label(text="Show:")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showCells")
        rowsub.prop(cfg, "struct_showLinks_legacy")

        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showLinks")
        rowsub.prop(cfg, "struct_showLinks_airLinks")

        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showPoints")
        rowsub.prop(cfg, "struct_showBB")
        rowsub.prop(cfg, "struct_showOrignal_scene")

        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showOrignal")
        rowsub.prop(cfg, "struct_showConvex")
        rowsub.prop(cfg, "struct_showLow")