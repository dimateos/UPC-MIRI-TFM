import bpy
import bpy.types as types

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)
from .properties_utils import Prop_inspector, RND_config, getProps_namesFiltered, getProps_splitDebug

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

def draw_toggleBox(metadata, propToggle_name:str, layout: types.UILayout, text:str=None, scaleBox=1, scaleOpen=0.9, returnCol=True) -> tuple[bool, types.UILayout]:
    """ Create a box with a toggle, scales down recursively inner widgets by default. Return the state of the toggle and the created layout."""
    box = layout.box()
    open = getattr(metadata, propToggle_name)
    icon = CONST_ICONS.section_opened if open else CONST_ICONS.section_closed

    # optinal reduced spacing
    if returnCol: box = box.column()
    box.scale_y = scaleBox*scaleOpen if open else scaleBox

    # draw title with icon
    box.prop(metadata, propToggle_name, toggle=True, icon=icon, text=text)

    return open, box

def draw_props_raw(data, prop_names:list[str], layout: types.UILayout, showId=False):
    """ Draw a list of object properties in a sub layout. """
    for prop_name in prop_names:
        if showId: layout.row().prop(data, prop_name, text=prop_name)
        else: layout.row().prop(data, prop_name)

def draw_props(data, propFilter:str, layout: types.UILayout, showId=False, showDefault=True):
    """ Query and draw all properties of an object in a sub layout. """
    # get the props filtered without the non prop ones
    prop_names = getProps_namesFiltered(data, propFilter, addDefault=showDefault, exc_nonBlProp=True)
    draw_props_raw(data, prop_names, layout, showId)

#-------------------------------------------------------------------

def draw_propsToggle_custom(data, data_inspector:Prop_inspector, layout:types.UILayout,
                            propToggle_name="meta_show_props", text:str=None,
                            propToggle_debug_name="meta_show_debug_props", text_debug:str=None,
                            propFilter="-meta,-debug", showDefault=True, showId=False, editable=True, splitDebug=False,
                            scaleBox=1, scaleOpen=0.9, scaleDebug=0.9, returnCol=True, userCustom=False) -> tuple[bool, types.UILayout]:
    """ Draw some properties of an object under a custom toggleable layout, inclues an inner debug toggle. """

    # outer fold
    open, box = draw_toggleBox(data_inspector, propToggle_name, layout, text, scaleBox, scaleOpen, returnCol)
    if open:
        # top of filter (fixed prop names)
        if userCustom:
            split = box.split(factor=0.25)
            split.prop(data_inspector, "meta_propShowId")
            split.prop(data_inspector, "meta_propDefault")
            split.prop(data_inspector, "meta_propEdit")
            box.prop(data_inspector, "meta_propFilter", text="")

        # filter props
        prop_names = getProps_namesFiltered(data, propFilter, addDefault=showDefault, exc_nonBlProp=True)

        # split debug props
        if splitDebug:
            prop_names, debug_names = getProps_splitDebug(prop_names)
            if (debug_names):
                # debug inner fold
                open_debug, box_debug = draw_toggleBox(data_inspector, propToggle_debug_name, box, text_debug, scaleBox=scaleDebug, scaleOpen=scaleOpen)
                if open_debug:
                    col = box_debug.column()
                    col.enabled = editable
                    draw_props_raw(data, debug_names, col, showId)

        # draw the list of props
        col         = box.column()
        col.enabled = editable
        draw_props_raw(data, prop_names, col, showId)

    return open, box

def draw_propsToggle_full(data, data_inspector:Prop_inspector, layout:types.UILayout, text:str="Properties",
                          splitDebug = True, scaleBox=1, scaleOpen=0.9, scaleDebug=0.9, returnCol=True, userCustom=True) -> tuple[bool, types.UILayout]:
    """ Draw some properties of an object under a custom toggleable layout, inclues an inner debug toggle. """

    # read from inspector some of the config
    propFilter = getattr(data_inspector, "meta_propFilter")
    showDefault = getattr(data_inspector, "meta_propDefault")
    showId = getattr(data_inspector, "meta_propShowId")
    editable = getattr(data_inspector, "meta_propEdit")

    return draw_propsToggle_custom(
        data, data_inspector, layout, text=text,
        propFilter=propFilter, showDefault=showDefault, showId=showId, editable=editable, splitDebug=splitDebug,
        scaleBox=scaleBox, scaleOpen=scaleOpen, scaleDebug=scaleDebug, returnCol=returnCol, userCustom=userCustom
        )

def draw_debug_rnd(layout:types.UILayout, rnd:RND_config):
    # rnd cfg out of debug
    row = layout.split(factor=0.55)
    row.prop(rnd, "seed")
    row = row.split()
    row.prop(rnd, "seed_mod", text="")
    row.prop(rnd, "seed_regen", text="regen")