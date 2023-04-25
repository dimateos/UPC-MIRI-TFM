import bpy
import bpy.types as types
import bpy.props as props


# Access from other modules to constants
class ADDON:
    _bl_info = None
    _bl_name = None
    mod_name = __name__
    mod_name_prefs = mod_name.split(".")[0]

    panel_cat = "Dev"


#-------------------------------------------------------------------

class MW_prefs(bpy.types.AddonPreferences):
    # XXX:: __name__ must be exaclty used for addon prefs, so check when deploying without the addon
    bl_idname = ADDON.mod_name_prefs

    def draw(self, context):
        # Careful with circulare dependecies, maybe split the class with draw and props
        from .ui import draw_propsToggle
        draw_propsToggle(self, self, "meta_show_prefs", "meta_propFilter", "meta_propEdit", self.layout)

    #-------------------------------------------------------------------

    meta_show_prefs: props.BoolProperty(
        name="Show addon preferences...", description="Show addon preferences",
        default=True,
    )
    meta_propFilter: props.StringProperty(
        name="FILTER", description="Separate values with commas, start with `-` for a excluding filter.",
        default="OT",
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

    OT_invert_shardNormals: props.BoolProperty(
        name="Invert final shards face normals", description="Seems like they end up reversed due to voro face ordering.",
        default=True,
    )

    OT_util_delete_unhide: props.BoolProperty(
        name="unhide", description="Unhide the original object after deletion",
        default=True,
    )

    #-------------------------------------------------------------------
    # XXX:: panels alone cannot store properties... here mixing dm panels with mw stuff, could separate the addons

    PT_info_edit_showWorld: props.BoolProperty(
        name="world space", description="Show vertices positions in world space",
        default=False,
    )
    PT_edit_showEdges: props.BoolProperty(
        name="Show edges...", description="Show long list of edges with its key (v1, v2)",
        default=False,
    )
    PT_edit_showFaceCenters: props.BoolProperty(
        name="center position", description="Show face center position instead of vertex indices",
        default=False,
    )

def getPrefs() -> MW_prefs:
    """ Get addon preferences from blender """
    return bpy.context.preferences.addons[MW_prefs.bl_idname].preferences


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_prefs,
]

def register():
    # Class declaration cannot be dynamic, so could assert afterwards
    #assert(MW_prefs.bl_idname == ADDON._bl_info["name"])
    assert(MW_prefs.bl_idname == ADDON._bl_name)

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)