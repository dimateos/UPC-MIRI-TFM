import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs
from .properties_root import (
    MW_id,
    MW_root,
)
from .properties_utils import Prop_inspector

from . import handlers
from . import utils
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
    default_key = 'PARTICLE_CHILD'
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

#-------------------------------------------------------------------

class MW_gen_cfg(types.PropertyGroup):

    # TODO:: maybe move to id too -> final fract with the global storage
    ptrID_links: props.StringProperty(default="nullptr")

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

    source_limit: props.IntProperty(
        name="Limit points", description="Limit the number of input points, 0 for unlimited",
        default=100, min=0, max=10000,
    )
    source_noise: props.FloatProperty(
        name="RND jitter", description="Jitter input point positions",
        default=0.0, min=0.0, max=1.0,
    )
    rnd_seed: props.IntProperty(
        name="RND seed", description="Seed the random generator, -1 to unseed it",
        default=64, min=-1,
    )

    #-------------------------------------------------------------------

    shape_useConvexHull: props.BoolProperty(
        name="Convex hull", description="Apply convex hull op beforehand",
        default=True,
    )
    shape_useWalls: props.BoolProperty(
        name="Wall planes", description="Keep the object faces as container walls (kind of like boolean op)",
        default=True,
    )

    margin_box_bounds: props.FloatProperty(
        name="Margin BB", description="Additional displacement of the box normal planes.",
        default=0.05, min=0.001, max=1.0, step=1, precision=3
    )
    margin_face_bounds: props.FloatProperty(
        name="Margin faces", description="Additional displacement of the face normal planes.",
        default=0.025, min=0.001, max=1.0, step=1, precision=3
    )

    #-------------------------------------------------------------------

    # TODO:: name here seems meh? + the functiuons
    # OPT:: example of having a per instance previous value of a property
    def struct_nameOriginal_update(self, context):
        #if self.struct_nameOriginal_prev == self.struct_nameOriginal: return # prev val is also reset on undo tho
        self.struct_nameOriginal_prev = self.struct_nameOriginal_prevRep
        self.struct_nameOriginal_prevRep = self.struct_nameOriginal
        DEV.log_msg(f"struct_nameOriginal: {self.struct_nameOriginal} - prev: {self.struct_nameOriginal_prev}", {"CALLBACK", "CFG", "PREV"})
    struct_nameOriginal: props.StringProperty(
        update= struct_nameOriginal_update
    )
    struct_nameOriginal_prevRep: props.StringProperty()
    struct_nameOriginal_prev: props.StringProperty()

    struct_namePrefix: props.StringProperty(
        name="Prefix",
        default="MW",
    )

    def get_struct_name(self):
        return f"{self.struct_namePrefix}_{self.struct_nameOriginal}"
    def get_struct_nameNew(self, newName):
        #self.struct_nameOriginal = newName
        return f"{self.struct_namePrefix}_{newName}"

    #-------------------------------------------------------------------
    # NOTE:: now the elements can be properly hidden while the last operator panel is open...
    # IDEA:: use for actually adding to the scene or not, otherwise not worth the recalculation

    struct_showShards: props.BoolProperty(
        name="Shards", description="Voronoi cells",
        default=True,
    )

    struct_showLinks: props.BoolProperty(
        name="WIP: Links", description="Voronoi cells links per face",
        default=True,
    )
    struct_showLinks_airLinks: props.BoolProperty(
        name="WIP: Links to walls", description="Voronoi cells links per face to walls",
        default=True,
    )
    struct_showLinks_legacy: props.BoolProperty(
        name="Cell links (centroid)", description="Links from centroids to neigh cells",
        default=False,
    )

    struct_showPoints: props.BoolProperty(
        name="Points", description="The ones used for the cells generation",
        default=True,
    )
    struct_showBB: props.BoolProperty(
        name="BB", description="The extended BB min max points, tobble show bounding box in viewport",
        default=True,
    )
    struct_showOrignal_scene: props.BoolProperty(
        name="Source Obj", description="The original object in the scene",
        default=False,
    )

    struct_showOrignal: props.BoolProperty(
        name="Original", description="The original object backup child",
        default=False,
    )
    struct_showConvex: props.BoolProperty(
        name="Convex", description="The original object convex hull",
        default=False,
    )
    struct_showLow: props.BoolProperty(
        name="WIP: Low", description="The convex hull decimated",
        default=False,
    )

    #-------------------------------------------------------------------

    def struct_linksScale_update(self, context):
        obj = MW_root.getSelected()
        if not obj: return
        links = utils.get_child(obj, getPrefs().names.links)
        if links: utils.scale_objectChildren(links, self.struct_linksScale)
        links_Air_Cell = utils.get_child(obj, getPrefs().names.links_air)
        if links_Air_Cell: utils.scale_objectChildren(links_Air_Cell, self.struct_linksScale)


    struct_linksScale: props.FloatProperty(
        name="Links scale", description="Reduce some bits to be able to see the links better",
        default=1, min=0.25, max=3,
        update=struct_linksScale_update
    )


#-------------------------------------------------------------------
# OPT:: maybe split files + some go to prefs + new propGroup to add to scene props_utils instead of prefs
# IDEA:: vis cfg part of each gen and sim, or subpart with another group?
# IDEA:: using animation frame handler to see the simulaion play?
# IDEA:: min -1 for infinite break condition?

class MW_sim_cfg(types.PropertyGroup):
    steps: props.IntProperty(
        name="Number of iters", description="WIP: atm redo each modification",
        default=1, min=1, max=1000,
    )
    subSteps: props.IntProperty(
        name="Number of propagations per iter", description="WIP: atm redo each modification",
        default=10, min=0, max=100,
    )

    steps_uniformDeg: props.BoolProperty(
        name="Uniform reduction",
        default=False,
    )
    steps_reset: props.BoolProperty(
        name="Reset at start",
        default=True,
    )

    deg: props.FloatProperty(
        name="Degradation", description="WIP: flat reduction",
        default=0.25, min=0.05, max=0.75, step=1, precision=3
    )

    addSeed: props.IntProperty(
        name="Add random seed",
        default=0, min=0, max=100,
    )


#-------------------------------------------------------------------

def cell_scale_update(self, context):
    obj = MW_root.getSelected()
    if not obj: return
    cells_root = utils.get_child(obj, getPrefs().names.shards)
    utils.scale_objectChildren(cells_root, self.cell_scale)

class MW_vis_cfg(types.PropertyGroup):

    cell_scale: props.FloatProperty(
        name="Cell scale", description="Reduce some bits to be able to see the links better",
        default=0.75, min=0.25, max=1.5,
        update=cell_scale_update
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


def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})