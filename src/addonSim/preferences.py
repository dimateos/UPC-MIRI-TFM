import bpy
import bpy.types as types
import bpy.props as props

# Careful with circulare dependecies
from .ui import draw_props

# Access from other modules to constants
class ADDON:
    _bl_info = None
    _bl_name = None
    mod_name = __name__
    mod_name_prefs = mod_name.split(".")[0]


# -------------------------------------------------------------------

class MW_prefs(bpy.types.AddonPreferences):
    # NOTE: MUST be the same as module name
    bl_idname = ADDON.mod_name_prefs

    def draw(self, context):
        draw_props(self, self.layout)

# -------------------------------------------------------------------

    # TODO:: rename cause the cfg meta props are the same and will be moved here
    meta_show_debug: props.BoolProperty(
        name="Show debug...",
        default=True,
        description="Show some debug preferences",
    )
    meta_show_prefs: props.BoolProperty(
        name="Show addon preferences...",
        default=True,
        description="Show addon preferences"
    )
    meta_propFilter: props.StringProperty(
        name="FILTER",
        default="-meta",
        description="Separate values with commas, start with `-` for a excluding filter."
    )
    meta_propEdit: props.BoolProperty(
        name="edit",
        default=True,
        description="Edit the props"
    )

# -------------------------------------------------------------------

    PT_info_edit_showWorld: props.BoolProperty(
        name="world space",
        description="Show vertices positions in world space",
        default=False,
    )
    PT_info_edit_showEdges: props.BoolProperty(
        name="Show edges...",
        default=False,
    )
    PT_info_edit_showFaceCenters: props.BoolProperty(
        name="center position",
        description="Show face center position instead of vertex indices",
        default=False,
    )

# -------------------------------------------------------------------

    OT_util_delete_unhide: props.BoolProperty(
        name="unhide",
        description="Unhide the original object after deletion",
        default=True,
    )

# -------------------------------------------------------------------

def getPrefs(context: types.Context) -> MW_prefs:
    """ Get addon preferences from blender """
    return context.preferences.addons[MW_prefs.bl_idname].preferences


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_prefs,
)

def register():
    # Class declaration cannot be dynamic, so could assert afterwards
    #assert(MW_prefs.bl_idname == ADDON._bl_info["name"])
    assert(MW_prefs.bl_idname == ADDON._bl_name)

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)