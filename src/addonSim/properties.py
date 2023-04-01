import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
    EnumProperty,
    FloatVectorProperty,
)

from tess import Container, Cell

# -------------------------------------------------------------------
# WIP sample properties

class MW_gen_cfg(bpy.types.PropertyGroup):
    source_noise: FloatProperty(
        name="Noise",
        description="Randomize point distribution",
        min=0.0, max=1.0,
        default=0.0,
    )

class MW_sim_cfg(bpy.types.PropertyGroup):
    source_limit: IntProperty(
        name="Source Limit",
        description="Limit the number of input points, 0 for unlimited",
        min=0, max=5000,
        default=100,
    )
    pass

class MW_vis_cfg(bpy.types.PropertyGroup):
    cell_scale: FloatVectorProperty(
        name="Scale",
        description="Scale Cell Shape",
        size=3,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
    )

class SnowSettings(bpy.types.PropertyGroup):
    coverage : IntProperty(
        name = "Coverage",
        description = "Percentage of the object to be covered with snow",
        default = 100,
        min = 0,
        max = 100,
        subtype = 'PERCENTAGE'
        )

    height : FloatProperty(
        name = "Height",
        description = "Height of the snow",
        default = 0.3,
        step = 1,
        precision = 2,
        min = 0.1,
        max = 1
        )

    vertices : BoolProperty(
        name = "Selected Faces",
        description = "Add snow only on selected faces",
        default = False
        )

    testRaw_int : int = 16
    testRaw_dict : dict = { "yes": "yes" }
    testRaw_class : Cell = Cell()

# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
    SnowSettings,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.mw_gen = PointerProperty(
        type=MW_gen_cfg,
        name="MW_Generation",
        description="MW generation properties")

    bpy.types.Object.mw_sim = PointerProperty(
        type=MW_sim_cfg,
        name="MW_Simulation",
        description="MW simulation properties")

    # WIP maybe visualization stored in scene?
    bpy.types.Object.mw_vis = PointerProperty(
        type=MW_vis_cfg,
        name="MW_Visualization",
        description="MW visualization properties")

    bpy.types.Scene.snow = PointerProperty(type=SnowSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.snow

