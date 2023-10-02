import bpy
import bpy.types as types
import bpy.props as props

from . import mw_setup_props
from . import properties_utils

from .utils_dev import DEV


#-------------------------------------------------------------------

# dynamic source options
class MW_gen_source_options:
    all=[
        ('VERT_OWN', "Own Verts", "Use own vertices (also set by default when other options are disabled)"),
        ('VERT_CHILD', "Child Verts", "Use child object vertices"),
        ('PARTICLE_OWN', "Own Particles", "All particle systems of the source object"),
        ('PARTICLE_CHILD', "Child Particles", "All particle systems of the child objects"),
        #('PENCIL', "Pencil", "Annotation Grease Pencil (only touching/inside the volume)"),
    ]
    all_keys = [ k[0] for k in all ]
    default_key = 'PARTICLE_OWN'
    fallback_key = 'VERT_OWN'
    error_key = 'NONE'
    error_option = [ (error_key, "No point found...", f"Options: {all_keys}") ]

def source_update_items(self, context):
    items = [
        t for t in MW_gen_source_options.all
            if t[0] in self.meta_source_enabled
    ]
    if items: return items
    else: return MW_gen_source_options.error_option.copy()


# dynamic naming
def struct_nameOriginal_update(self, context):
    # NOTE:: unused example of having a per instance previous value of a property
    #if self.meta_nameOriginal_prev == self.meta_nameOriginal: return # prev val is also reset on undo tho
    self.meta_nameOriginal_prev = self.meta_nameOriginal_prevRep
    self.meta_nameOriginal_prevRep = self.struct_nameOriginal
    DEV.log_msg(f"struct_nameOriginal: {self.struct_nameOriginal} - prev: {self.meta_nameOriginal_prev}", {"CALLBACK", "CFG", "PREV"})

#-------------------------------------------------------------------

class MW_gen_cfg(types.PropertyGroup):

    # Set all available gen extractions
    meta_source_enabled: props.EnumProperty(
        name="Source all types",
        items=MW_gen_source_options.all.copy(),
        default={ MW_gen_source_options.fallback_key },
        options={'ENUM_FLAG'},
    )

    # Picked extraction method
    source: props.EnumProperty(
        name="Source", description="Available source from where to retrieve points",
        items=source_update_items, # default with numberID doesnt seem to work
        options={'ENUM_FLAG'},
    )
    source_numFound: props.IntProperty(
        name="Found points", description="Number of points found",
    )

    # mod source input points
    source_limit: props.IntProperty(
        name="Limit points", description="Limit the number of input points, 0 for unlimited",
        default=100, min=0, max=10000,
    )
    source_shuffle: props.BoolProperty(
        name="RND order", description="Shuffle input points",
        default=True,
    )
    source_noise: props.FloatProperty(
        name="RND jitter", description="Jitter input point positions",
        default=0.0, min=0.0, max=1.0, precision=2, step=1
    )

    # mod faces container shape
    shape_useConvexHull: props.BoolProperty(
        name="Convex hull", description="Apply convex hull op beforehand",
        default=False, # upZ oriented hill gets BAD normals when doing the convex hull...
    )
    shape_useWalls: props.BoolProperty(
        name="Wall planes", description="Keep the object faces as container walls (kind of like boolean op)",
        default=True,
    )
    margin_box_bounds: props.FloatProperty(
        name="Margin BB", description="Additional displacement of the box normal planes.",
        default=0.1, min=0.001, max=1.0, step=1, precision=3
    )
    margin_face_bounds: props.FloatProperty(
        name="Margin F", description="Additional displacement of the face normal planes.",
        default=0.1, min=0.001, max=1.0, step=1, precision=3
    )

    #-------------------------------------------------------------------

    debug_rnd: props.PointerProperty(type=properties_utils.RND_config)

    debug_precisionWalls: props.IntProperty(
        # OPT:: edit more voro configs? even recompile like with test scripts?
        name="Limit wall precision", description="Number of decimals used to round and cluster wall planes",
        default=4, min=0, max=10,
    )

    debug_ensure_noDoubles: props.BoolProperty(
        name="Ensure no repeated input points", description="Collapse the input point to a set of unique pointers before building the container",
        default=True,
    )

    debug_flipCellNormals: props.BoolProperty(
        name="Flip final cell normals", description="Seems like they end up reversed due to voro face ordering",
        default=True,
    )

    #debug_gen_links: props.BoolProperty(
    #    name="Generate links mesh directly", description="Otherwise generated later by the operator buton un the gen panel.",
    #    default=True,
    #)
    debug_fieldR: props.BoolProperty(
        name="Generate R field visuals", description="You can later modify the geometry and update the visualization.",
        default=True,
    )
    debug_fieldR_res: props.IntProperty(
        name="Generated R field resolution", description="Resolution of the grid used for visualization, could slow substantially generation.",
        default=2,
        min=1, max=16
    )

    #-------------------------------------------------------------------

    # mod final fract object name
    struct_namePrefix: props.StringProperty(
        name="Prefix",
        default="MW",
    )
    struct_nameOriginal: props.StringProperty(
        update= struct_nameOriginal_update
    )
    meta_nameOriginal_prevRep: props.StringProperty()
    meta_nameOriginal_prev: props.StringProperty()


#-------------------------------------------------------------------

class MW_sim_cfg(types.PropertyGroup):
    # main params shown with step prefix
    step_infiltrations: props.IntProperty(
        name="Number of infiltrations",
        description="Translate to individual paths traced per button press.",
        default=1, min=1, max=1000,
    )
    step_maxDepth: props.IntProperty(
        name="Max infiltrations depth",
        description="Limit water depth, set to -1 to let all water to be absorbed.",
        default=10, min=-1, max=100,
    )

    # water start and abs
    water__start: props.FloatProperty(
        name="Water input amount",
        description="Initial water amount.",
        default=1.0, min=0.1, max=2.5,
    )
    water_deg: props.FloatProperty(
        name="Water degradation", description="Amount of water absorbed when eroding a link, affected by link resistance.",
        default=0.25,
        min=0.05, max=1.0,
    )
    water_abs_air: props.FloatProperty(
        name="Water air abs",
        description="Amount of water absorbed by the average surface area through a non solid link",
        default=0.05,
        min=0.005, max=0.5, precision=3
    )
    water_abs_solid: props.FloatProperty(
        name="Water solid abs",
        description="Amount of water absorbed by the average surface area through a solid link",
        default=0.10,
        min=0.005, max=0.5, precision=3
    )

    # simple link deg
    link_deg: props.FloatProperty(
        name="Link degradation", description="Amount of erosion water does to a link, distributed over its area.",
        default=0.5,
        min=0.05, max=1.0,
    )
    link_resist_weight: props.FloatProperty(
        name="Link resistance", description="Control over the effecto of the resistance field",
        default=0.75,
        min=0.05, max=1.0,
    )

    #-------------------------------------------------------------------

    # dir aligments
    dir_entry: props.FloatVectorProperty(
        description="Kind of wind direction carrying input water (normalized for execution)",
        subtype='XYZ',
        size=3,
        default=(1, -0.5, -0.5),
        #default=(0, 1, 0),
    )
    dir_entry_minAlign: props.FloatProperty(
        description="Min aligment required, otherwise unreacheable",
        default=0.1, precision=3,
        min=-1.0, max=1.0
    )
    dir_next: props.FloatVectorProperty(
        description="Kind of gravity direction followed by the water inside the model , (normalized for execution)",
        subtype='XYZ',
        size=3,
        default=(0, 0, -1),
    )
    dir_next_minAlign: props.FloatProperty(
        description="Min aligment required, otherwise unreacheable",
        default=0.1, precision=3,
        min=-1.0, max=1.0
    )

    # water absorption random event
    water_rnd_abs_minCheck: props.FloatProperty(
        description="Amount of water min to start checking for rnd full absorption",
        default=0.25, min=0.05, max=0.5
    )
    water_rnd_abs_continueProb: props.FloatProperty(
        description="Probability to continue flowing when water is at water_rnd_abs_minCheck",
        default=0.9, min=0.0, max=1.0
    )
    water_rnd_abs_damage: props.FloatProperty(
        description="Amount of water min to start checking for rnd full absorption",
        default=0.75, min=0.0, max=1.0
    )

    # link break random event
    link_rnd_break_minCheck: props.FloatProperty(
        description="Amount of link life min to start checking for rnd break event",
        default=0.4, min=0.05, max=0.5
    )
    link_rnd_break_resistProb: props.FloatProperty(
        description="Probability to withstand the break when the link life is at water_rnd_abs_minCheck",
        default=0.9, min=0.0, max=1.0
    )

    #-------------------------------------------------------------------

    #debug_stopBreak_event: props.EnumProperty(
    #    name="Select where to stop the ",
    #    items=(
    #        ('LINK', "Disabled", "No effect on width"),
    #        ('CELL', "Uniform effect", "Uniform effect on width"),
    #    ),
    #    default={'LINK'},
    #    options={'ENUM_FLAG'},
    #    update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links_width__mode")
    #)

    #debug_stopBreak_onLink: props.BoolProperty(
    #    name="Stop on link break",
    #    description="Stop on link or cell break",
    #    default=True,
    #)

    debug_rnd: props.PointerProperty(type=properties_utils.RND_config)

    # cfg logging
    debug_log: props.BoolProperty(
        description="Output some info during simulation",
        default=True,
    )
    debug_log_path: props.BoolProperty(
        description="Write the full final path",
        default=True,
    )
    debug_log_trace: props.BoolProperty(
        description="SLOW: Keep a complete log of the path along with props",
        default=False,
    )
    debug_log_trace_candidates: props.BoolProperty(
        description="SLOWER: Show all candidates and their probabilty per substep",
        default=False,
    )

    # custom sim/vis
    debug_skip_entry_area: props.BoolProperty(
        name="DEBUG: skip entry L area",
        description="Skip area entry weight to only vis alignment",
        default=False,
    )
    debug_skipVis_entry_unreachProb: props.BoolProperty(
        name="DEBUG: no vis null entry L",
        description="Skip vis of unreachable entry links",
        default=True,
    )
    debug_skip_next_maxResist: props.BoolProperty(
        name="DEBUG: skip max resist L",
        description="Completely skip links with max resist",
        default=False,
    )
    #debug_skip_next_area: props.BoolProperty(
    #    name="DEBUG: skip next area reistance weight",
    #    default=False,
    #)

    # test erosion
    debug_util_rndState: props.BoolProperty(
        name="TEST: rnd init",
        description="Initial random link state (within some limits)",
        default=False,
    )
    debug_util_uniformDeg: props.BoolProperty(
        name="TEST: uniform deg",
        description="Uniform erosion to all links",
        default=False,
    )

#-------------------------------------------------------------------

class MW_vis_cfg(types.PropertyGroup):
    from .preferences import getPrefs

    # use prefs editor in the panel but edit the selected root
    nbl_prefsProxy: props.BoolProperty(default=False)

    #-------------------------------------------------------------------

    cell_scale: props.FloatProperty(
        name="Cell scale", description="Reduce some bits to be able to see the links better",
        default=0.75, min=0.25, max=1.0,
        update= lambda self, context: mw_setup_props.cell_scale_update(self)
    )

    cell_color: bpy.props.FloatVectorProperty(
        name="Cell SOLID color",
        default=(0.514, 0.396, 0.224, 0.75),
        size=4, min=0, max=1,
        subtype='COLOR',
        update= lambda self, context: mw_setup_props.cell_color_update(self, "cell_color", MW_vis_cfg.getPrefs().names.cells)
    )
    cell_color_air: bpy.props.FloatVectorProperty(
        name="Cell AIR color",
        default=(0, 0.7, 1, 0.05),
        size=4, min=0, max=1,
        subtype='COLOR',
        update= lambda self, context: mw_setup_props.cell_color_update(self, "cell_color_air", MW_vis_cfg.getPrefs().names.cells_air)
    )
    cell_color_core: bpy.props.FloatVectorProperty(
        name="Cell CORE color",
        default=(0.8, 0.294, 0.125, 1.0),
        size=4, min=0, max=1,
        subtype='COLOR',
        update= lambda self, context: mw_setup_props.cell_color_update(self, "cell_color_core", MW_vis_cfg.getPrefs().names.cells_core)
    )

    #-------------------------------------------------------------------

    links_smoothShade: props.BoolProperty(
        name="Link smooth shade",
        default=False,
        update= lambda self, context: mw_setup_props.links_smoothShade_update(self)
    )

    #-------------------------------------------------------------------
    # debug one are non-dynamic, only affects subsequent runs but get written to root too
    # OPT:: most could be easily dynamic but probably not worth it or jus regen all mesh

    links__show: props.BoolProperty(
        name="Links",
        default=True,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links__show")
    )

    links_depth: props.FloatProperty(
        name="Link depth", description="Minimun depth inside faces",
        default=0.1, min=0.01, max=0.4, step=0.05, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links_depth")
    )
    links_width_base: props.FloatProperty(
        name="Link width base",
        default=0.05, min=0.01, max=0.2, step=0.01, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links_width_base")
    )
    links_width_broken: props.FloatProperty(
        name="Link width broken",
        default=0.005, min=0.001, max=0.001, step=0.05, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links_width_broken")
    )

    links_width__mode: props.EnumProperty(
        name="Link dynamic width",
        items=(
            ('DISABLED', "Disabled", "No effect on width"),
            ('UNIFORM', "Uniform effect", "Uniform effect on width"),
            ('BINARY', "Binary", "Any differece from full life affects drastically"),
        ),
        default={'UNIFORM'},
        options={'ENUM_FLAG'},
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links_width__mode")
    )

    links_res: props.IntProperty(
        name="Link mesh resolution", description="Affect the number of faces per tube",
        default=1, min=-1, max=8,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "links_res")
    )

    #-------------------------------------------------------------------

    neighs__show: props.BoolProperty(
        name="Inner neigh links",
        default=False,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "neighs__show")
    )

    neighs_width: props.FloatProperty(
        name="Inner neigh links width",
        default=0.01, min=0.0025, max=0.05, step=0.05, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "neighs_width")
    )

    neighs_res: props.IntProperty(
        name="Inner neigh links res", description="Affect the number of faces per tube",
        default=-1, min=-1, max=8,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "neighs_res")
    )

    #-------------------------------------------------------------------

    path__show: props.BoolProperty(
        name="Path",
        default=True,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path__show")
    )

    path_outside_start: props.FloatProperty(
        name="Path outside start tail", description="Initial water from outside starts at an arbitrary pos",
        default=1, min=0.5, max=2.5,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_outside_start")
    )
    path_outside_end: props.BoolProperty(
        name="Path outside end tail", description="Clearly see the water exit path",
        default=True,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_outside_end")
    )

    path_width_start: props.FloatProperty(
        name="Path width start", description="Represents full initial water",
        default=0.05, min=0.01, max=0.2, step=0.01, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_width_start")
    )
    path_width_end: props.FloatProperty(
        name="Path width end", description="Represents no more water",
        default=0.005, min=0.001, max=0.001, step=0.05, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_width_end")
    )

    path_res: props.IntProperty(
        name="Path mesh resolution", description="Affect the number of faces per tube",
        default=0, min=-1, max=8,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_res")
    )
    path_alpha: props.FloatProperty(
        name="Path mat alpha", description="Help seeing through",
        default=0.9, min=0.1, max=1.0,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_alpha")
    )
    path_dark_end: props.FloatProperty(
        name="Path darker end", description="Darken color along the path",
        default=1.0, min=0.0, max=1.0,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "path_dark_end")
    )

    #-------------------------------------------------------------------

    wall_links__show: props.BoolProperty(
        name="Air links entry",
        default=True,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "wall_links__show")
    )
    wall_links_show_picks: props.BoolProperty(
        name="Air links water picks",
        default=False,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "wall_links__show")
    )

    wall_links_depth_base: props.FloatProperty(
        name="Air link depth base",
        default=0.1, min=0.05, max=0.5, step=0.05, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "wall_links_depth_base")
    )
    wall_links_depth_incr: props.FloatProperty(
        name="Air link depth incr",
        default=0.05, min=0.01, max=0.1, step=0.01, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "wall_links_depth_incr")
    )
    wall_links_width_base: props.FloatProperty(
        name="Air link width",
        default=0.075, min=0.05, max=0.5, step=0.1, precision=4,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "wall_links_width_base")
    )

    wall_links_res: props.IntProperty(
        name="Air link resolution", description="Affect the number of faces per tube",
        default=0, min=-1, max=8,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "wall_links_res")
    )

    #-------------------------------------------------------------------

    water_dir__show: props.BoolProperty(
        name="Water dir arrow",
        default=True,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "water_dir__show")
    )
    water_dir_scale: props.FloatProperty(
        name="Water dir arrow scale",
        default=1.5,
        update= lambda self, context: mw_setup_props.getRoot_checkProxy_None(self, "mw_vis", "water_dir_scale")
    )

#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    for cls in classes:
        bpy.utils.register_class(cls)

    # appear as part of default object props
    # NOTE:: only non-default values of property groups get stored in objects memory, there are optimizations

    bpy.types.Object.mw_gen = props.PointerProperty(
        type=MW_gen_cfg,
        name="MW_Generation", description="MW generation properties")

    bpy.types.Object.mw_sim = props.PointerProperty(
        type=MW_sim_cfg,
        name="MW_Simulation", description="MW simulation properties")

    bpy.types.Object.mw_vis = props.PointerProperty(
        type=MW_vis_cfg,
        name="MW_Visualization", description="MW visualization properties")

    # add as scene to overwrite default values (kind of like OP having cfg)
    # NOTE:: affected by undo stack! so better to store in prefs
    #bpy.types.Scene.mw_vis = props.PointerProperty(type=MW_vis_cfg)


def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    #del bpy.types.Scene.mw_vis


DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})