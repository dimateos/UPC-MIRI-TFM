import bpy
import bpy.types as types
import bpy.props as props


# Access from other modules to constants
class ADDON:
    _bl_info = None
    _bl_name = None
    mod_name = __name__
    mod_name_prefs = mod_name.split(".")[0]


#-------------------------------------------------------------------

class MW_prefs(bpy.types.AddonPreferences):
    # XXX:: __name__ must be exaclty used for addon prefs, so check when deploying without the addon
    bl_idname = ADDON.mod_name_prefs

    def draw(self, context):
        # Careful with circulare dependecies, maybe split the class with draw and props
        from .ui import draw_props
        draw_props(self, self.layout)

    #-------------------------------------------------------------------

    meta_show_prefs: props.BoolProperty(
        name="Show addon preferences...", description="Show addon preferences",
        default=True,
    )
    meta_propFilter: props.StringProperty(
        name="FILTER", description="Separate values with commas, start with `-` for a excluding filter.",
        default="-meta",
    )
    meta_propEdit: props.BoolProperty(
        name="edit", description="Edit the props",
        default=True,
    )

    meta_show_tmpDebug: props.BoolProperty(
        name="Show debug...", description="WIP: Show some debug stuff",
        default=True,
    )

    #-------------------------------------------------------------------

    PT_gen_show_summary: props.BoolProperty(
        name="Show object summary...", description="Show fracture summary",
        default=False,
    )
    PT_gen_propFilter: props.StringProperty(
        name="FILTER", description="Separate values with commas, start with `-` for a excluding filter.",
        default="-meta",
    )
    PT_gen_propEdit: props.BoolProperty(
        name="edit", description="Edit the props",
        default=False,
    )

    PT_gen_show_tmpDebug: props.BoolProperty(
        name="Show DEBUG...", description="WIP: Show some debug stuff",
        default=True,
    )

    #-------------------------------------------------------------------

    PT_info_edit_showWorld: props.BoolProperty(
        name="world space", description="Show vertices positions in world space",
        default=False,
    )
    PT_info_edit_showEdges: props.BoolProperty(
        name="Show edges...", description="Show long list of edges with its key (v1, v2)",
        default=False,
    )
    PT_info_edit_showFaceCenters: props.BoolProperty(
        name="center position", description="Show face center position instead of vertex indices",
        default=False,
    )

    OT_util_delete_unhide: props.BoolProperty(
        name="unhide", description="Unhide the original object after deletion",
        default=True,
    )


def getPrefs() -> MW_prefs:
    """ Get addon preferences from blender """
    return bpy.context.preferences.addons[MW_prefs.bl_idname].preferences


#-------------------------------------------------------------------
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