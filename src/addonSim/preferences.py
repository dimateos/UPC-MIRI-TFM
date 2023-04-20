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

def getPrefs(context: types.Context):
    return context.preferences.addons[MW_prefs.bl_idname].preferences

class MW_prefs(bpy.types.AddonPreferences):
    # NOTE: MUST be the same as module name
    bl_idname = ADDON.mod_name_prefs

    def draw(self, context):
        draw_props(self, self.layout)

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

    OT_util_delete_unhide: props.BoolProperty(
        name="unhide",
        description="Unhide the original object after deletion",
        default=True,
    )


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