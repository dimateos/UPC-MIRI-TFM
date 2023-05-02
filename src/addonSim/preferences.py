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
        draw_propsToggle(self, self, "prefs_PT_meta_show_prefs", "prefs_PT_meta_propFilter", "prefs_PT_meta_propEdit", "prefs_PT_meta_propShowId", self.layout)

    # meta filter for addon prefs
    prefs_PT_meta_show_prefs: props.BoolProperty(
        name="Show addon preferences...", description="Show addon preferences",
        default=True,
    )
    prefs_PT_meta_propFilter: props.StringProperty(
        name="FILTER", description="Separate values with commas, start with `-` for a excluding filter.",
        default="-PT,",
    )
    prefs_PT_meta_propEdit: props.BoolProperty(
        name="edit", description="Edit the props",
        default=True,
    )
    prefs_PT_meta_propShowId: props.BoolProperty(
        name="id", description="Show property id or its name",
        default=True,
    )

    prefs_PT_meta_show_tmpDebug: props.BoolProperty(
        name="Show debug...", description="WIP: Show some debug stuff",
        default=True,
    )

    #-------------------------------------------------------------------

    # meta filter for OP props
    gen_PT_meta_show_summary: props.BoolProperty(
        name="Show object summary...", description="Show fracture summary",
        default=False,
    )
    gen_PT_meta_propFilter: props.StringProperty(
        name="FILTER", description="Separate values with commas, start with `-` for a excluding filter.",
        default="-show",
    )
    gen_PT_meta_propEdit: props.BoolProperty(
        name="edit", description="Edit the props",
        default=False,
    )
    get_PT_meta_propShowId: props.BoolProperty(
        name="id", description="Show property id or its name",
        default=True,
    )

    #gen_PT_meta_show_visuals: props.BoolProperty(
    #    name="Show visual toggle...", description="Toggle fracture elements ",
    #    default=True,
    #)
    gen_PT_meta_show_tmpDebug: props.BoolProperty(
        name="Show DEBUG...", description="WIP: Show some debug stuff",
        default=True,
    )

    #-------------------------------------------------------------------
    # TODO:: what to store per object and what in prefs? could be in object but edit from panel

    ## IDEA:: global rnd needed?
    #calc_defaultSeed: props.IntProperty(
    #    name="Default random seed", description="Leave <0 for random",
    #    default=64, min=-1,
    #)

    gen_calc_precisionWalls: props.IntProperty(
        # OPT:: read voro++ config from python? API/file system
        name="Wall precision", description="Number of decimals used to round and cluster wall planes",
        default=4, min=0, max=10,
    )

    gen_setup_invertShardNormals: props.BoolProperty(
        name="Invert final shards face normals", description="Seems like they end up reversed due to voro face ordering.",
        default=True,
    )

    #-------------------------------------------------------------------

    util_delete_OT_unhideSelect: props.BoolProperty(
        name="unhide", description="Unhide the original object after deletion",
        default=True,
    )

    #-------------------------------------------------------------------
    # NOTE:: panels alone cannot store properties... here mixing dm panels with mw stuff, could separate the addons
    # OPT:: quite similar options as the spawn indices OP

    dm_PT_meta_show_info: props.BoolProperty(
        name="Show inspect...", description="Show the object info",
        default=True,
    )
    dm_PT_meta_show_full: props.BoolProperty(
        name="Show full...", description="Show all the info",
        default=False,
    )

    # filters
    dm_PT_edit_useSelected: props.BoolProperty(
        name="Use selected", description="Show the selected mesh data (NOT UPDATED LIVE)",
        default=True,
    )
    dm_PT_edit_showLimit: props.IntProperty(
        name="limit", description="Max number of items shown per type (blender has a limit size of scrollable UI area)",
        default=20, min=1, max=50,
    )
    dm_PT_edit_indexFilter: props.StringProperty(
        name="Indices", description="Range '2_20' (20 not included). Specifics '2,6,7'. Both '0_10,-1' ('-' for negative indices)",
        default="0_3,-1",
    )

    # edit options
    dm_PT_edit_showVerts: props.BoolProperty(
        name="Show verts...", description="Show long list of verts with its pos",
        default=False,
    )
    dm_PT_edit_showEdges: props.BoolProperty(
        name="Show edges...", description="Show long list of edges with its key (v1, v2)",
        default=False,
    )
    dm_PT_edit_showFaces: props.BoolProperty(
        name="Show faces...", description="Show long list of faces with its verts id / center",
        default=True,
    )
    dm_PT_edit_showFaceCenters: props.BoolProperty(
        name="show center", description="Show face center position instead of vertex indices",
        default=False,
    )

    # toggle visual
    dm_PT_info_showPrecision: props.IntProperty(
        name="decimals", description="Number of decimals shown, will make colum wider.",
        default=2, min=0, max=16,
    )
    dm_PT_info_edit_showWorld: props.BoolProperty(
        name="world", description="Show vertices positions in world space",
        default=False,
    )

    #-------------------------------------------------------------------

    dm_PT_meta_show_tmpDebug: props.BoolProperty(
        name="Show debug...", description="WIP: Show some debug stuff",
        default=True,
    )
    dm_PT_orphans_collection: props.StringProperty(
        name="", description="E.g. meshes, curves, etc",
        default="meshes, curves",
    )

#-------------------------------------------------------------------

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