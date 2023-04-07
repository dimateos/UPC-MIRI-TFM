import bpy
import bpy.types as types
import bpy.props as props

from tess import Container, Cell


# -------------------------------------------------------------------
# WIP sample properties

class MW_gen_cfg(types.PropertyGroup):
    meta_refresh: props.BoolProperty(
        name="Refresh",
        default=False,
        description="Refresh once on click"
    )
    meta_auto_refresh: props.BoolProperty(
        name="Auto-Refresh",
        default=True,
        description="Automatic refresh"
    )
    meta_type: props.EnumProperty(
        name="Type",
        items=(
            ('NONE', "No fracture", "No fracture generated"),
            ('ROOT', "Root object", "Root object holding the fracture"),
            ('CHILD', "Child object", "Child object part of the fracture"),
        ),
        options={'ENUM_FLAG'},
        default={'NONE'},
    )
    meta_show_debug: props.BoolProperty(
        name="Show DEBUG...",
        default=True,
        description="Show some debug properties"
    )
    meta_show_summary: props.BoolProperty(
        name="Show summary...",
        default=True,
        description="Show fracture summary"
    )

    source: props.EnumProperty(
        name="Source",
        items=(
            ('VERT_OWN', "Own Verts", "Use own vertices"),
            ('VERT_CHILD', "Child Verts", "Use child object vertices"),
            ('PARTICLE_OWN', "Own Particles", "All particle systems of the source object"),
            ('PARTICLE_CHILD', "Child Particles", "All particle systems of the child objects"),
            #('PENCIL', "Annotation Pencil", "Annotation Grease Pencil."),
        ),
        options={'ENUM_FLAG'},
        default={'VERT_OWN'},
    )
    source_limit: props.IntProperty(
        name="Limit points",
        description="Limit the number of input points, 0 for unlimited",
        min=0, max=5000,
        default=100,
    )
    source_noise: props.FloatProperty(
        name="RND noise",
        description="Randomize point distribution",
        min=0.0, max=1.0,
        default=0.0,
    )

    #cell_scale: props.FloatVectorProperty(
    #    name="Cell scale",
    #    description="Scale Cell Shape",
    #    size=3,
    #    min=0.0, max=1.0,
    #    default=(1.0, 1.0, 1.0),
    #)

    margin_box_bounds: props.FloatProperty(
        name="Bounding box",
        description="Additional displacement of the box normal planes",
        min=0.0, max=1.0,
        default=0.025,
    )
    margin_face_bounds: props.FloatProperty(
        name="Normal faces",
        description="Additional displacement of the face normal planes",
        min=0.0, max=1.0,
        default=0.025,
    )

    struct_sufix: props.StringProperty(
        name="Sufix",
        default="MW",
    )
    struct_original: props.StringProperty()


class MW_sim_cfg(types.PropertyGroup):
    pass

class MW_vis_cfg(types.PropertyGroup):
    pass

# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.mw_gen = props.PointerProperty(
        type=MW_gen_cfg,
        name="MW_Generation",
        description="MW generation properties")

    bpy.types.Object.mw_sim = props.PointerProperty(
        type=MW_sim_cfg,
        name="MW_Simulation",
        description="MW simulation properties")

    # WIP maybe visualization stored in scene?
    bpy.types.Object.mw_vis = props.PointerProperty(
        type=MW_vis_cfg,
        name="MW_Visualization",
        description="MW visualization properties")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

