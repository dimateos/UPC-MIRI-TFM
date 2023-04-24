import bpy
import bpy.types as types
import bpy.props as props

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
        # Careful with circulare dependecies, maybe split the class with draw and props
        from .ui import draw_props
        draw_props(self, self.layout)

# -------------------------------------------------------------------

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

    meta_show_tmpDebug: props.BoolProperty(
        name="Show debug...",
        default=True,
        description="WIP: Show some debug stuff",
    )

# -------------------------------------------------------------------

    PT_gen_show_summary: props.BoolProperty(
        name="Show object summary...",
        default=False,
        description="Show fracture summary"
    )
    PT_gen_propFilter: props.StringProperty(
        name="FILTER",
        default="-meta",
        description="Separate values with commas, start with `-` for a excluding filter."
    )
    PT_gen_propEdit: props.BoolProperty(
        name="edit",
        default=False,
        description="Edit the props"
    )

    PT_gen_show_tmpDebug: props.BoolProperty(
        name="Show DEBUG...",
        default=True,
        description="WIP: Show some debug stuff"
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

    OT_util_delete_unhide: props.BoolProperty(
        name="unhide",
        description="Unhide the original object after deletion",
        default=True,
    )


def getPrefs() -> MW_prefs:
    """ Get addon preferences from blender """
    return bpy.context.preferences.addons[MW_prefs.bl_idname].preferences


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