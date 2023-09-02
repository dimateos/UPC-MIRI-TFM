import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs
from .properties_global import MW_global_selected

from . import utils_scene, utils_trans
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

def get_struct_name(cfg):
    return f"{cfg.struct_namePrefix}_{cfg.struct_nameOriginal}"
def get_struct_nameNew(cfg, newName):
    #self.struct_nameOriginal = newName
    return f"{cfg.struct_namePrefix}_{newName}"

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
        default=0.1, min=0.0, max=1.0,
    )

    # mod faces container shape
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
        default=0.1, min=0.001, max=1.0, step=1, precision=3
    )
    margin_face_bounds: props.FloatProperty(
        name="Margin F", description="Additional displacement of the face normal planes.",
        default=0.1, min=0.001, max=1.0, step=1, precision=3
    )

    #-------------------------------------------------------------------

    debug_rnd_seed: props.IntProperty(
        name="RND seed", description="Seed the random generator, -1 to unseed it",
        default=64, min=-1,
    )

    debug_precisionWalls: props.IntProperty(
        # OPT:: edit more voro configs? even recompile like with test scripts?
        name="Wall precision", description="Number of decimals used to round and cluster wall planes",
        default=4, min=0, max=10,
    )

    debug_flipCellNormals: props.BoolProperty(
        name="Invert final cells face normals", description="Seems like they end up reversed due to voro face ordering.",
        default=True,
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

    def struct_linksScale_update(self, context):
        obj = MW_global_selected.root
        if not obj: return
        links = utils_scene.get_child(obj, getPrefs().names.links)
        if links: utils_trans.scale_objectChildren(links, self.struct_linksScale)
        links_Air_Cell = utils_scene.get_child(obj, getPrefs().names.links_air)
        if links_Air_Cell: utils_trans.scale_objectChildren(links_Air_Cell, self.struct_linksScale)

    struct_linksScale: props.FloatProperty(
        name="Links scale", description="Reduce some bits to be able to see the links better",
        default=1, min=0.25, max=3,
        update=struct_linksScale_update
    )


#-------------------------------------------------------------------

def cell_scale_update(self, context):
    obj = MW_global_selected.root
    if not obj: return
    cells_root = utils_scene.get_child(obj, getPrefs().names.cells)
    utils_trans.scale_objectChildren(cells_root, self.cell_scale)

class MW_vis_cfg(types.PropertyGroup):

    cell_scale: props.FloatProperty(
        name="Cell scale", description="Reduce some bits to be able to see the links better",
        default=0.75, min=0.25, max=1.0,
        update=cell_scale_update
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
# Blender events

classes = [
    MW_gen_cfg,
    MW_vis_cfg,
    MW_sim_cfg,
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