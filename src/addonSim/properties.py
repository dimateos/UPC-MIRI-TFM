import bpy
import bpy.types as types
import bpy.props as props

from tess import Container, Cell

# -------------------------------------------------------------------
# WIP sample properties

class MW_gen_cfg(types.PropertyGroup):
    generated: props.BoolProperty()

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
        name="Source limit",
        description="Limit the number of input points, 0 for unlimited",
        min=0, max=5000,
        default=100,
    )
    source_noise: props.FloatProperty(
        name="Source noise",
        description="Randomize point distribution",
        min=0.0, max=1.0,
        default=0.0,
    )
    cell_scale: props.FloatVectorProperty(
        name="Cell scale",
        description="Scale Cell Shape",
        size=3,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    margin_box_bounds: props.FloatProperty(
        name="Margin box",
        description="Additional displacement of the box normal planes",
        min=0.0, max=1.0,
        default=0.025,
    )
    margin_face_bounds: props.FloatProperty(
        name="Margin faces",
        description="Additional displacement of the face normal planes",
        min=0.0, max=1.0,
        default=0.025,
    )

    copy_sufix: props.StringProperty(
        name="Copy name sufix",
        default="_fractured",
    )



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

