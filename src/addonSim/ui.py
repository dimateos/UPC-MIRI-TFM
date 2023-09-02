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


# Ui common functions
#-------------------------------------------------------------------

def draw_refresh(data, layout: types.UILayout):
    row = layout.box().row()
    row.scale_y = 1.5
    split = row.split(factor=0.75)
    split.prop(data, "meta_auto_refresh", toggle=True, icon_only=False, icon='FILE_REFRESH')
    split.prop(data, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

def draw_toggleBox(metadata, propToggle_name:str, layout: types.UILayout, text:str=None, scaleOpen=0.9) -> tuple[bool, types.UILayout]:
    """ Create a box with a toggle, scales down recursively inner widgets by default. Return the state of the toggle and the created layout."""
    box = layout.box()
    open = getattr(metadata, propToggle_name)
    icon = CONST_ICONS.section_opened if open else CONST_ICONS.section_closed

    if open:
        box.scale_y = scaleOpen

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
        split = box.split(factor=0.25)
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
                            propFilter="-meta", showDefault=True, showId=False, editable=True) -> tuple[bool, types.UILayout]:
    """ Draw some properties of an object under a custom toggleable layout. """

    # outer fold
    open, box = draw_toggleBox(data_inspector, "meta_show_props", layout, text)
    if open:
        prop_names = getProps_namesFiltered(data, propFilter, exc_nonBlProp=True, showDefault=showDefault)
        col         = box.column()
        col.enabled = editable
        draw_props_raw(data, prop_names, col, showId)

    return open, box
