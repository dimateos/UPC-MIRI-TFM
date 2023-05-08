import bpy
import bpy.types as types
import bpy.props as props

from . import handlers

# OPT:: seems bad to reference this here tho
from .mw_links import LinkStorage

from .utils_dev import DEV

# Access from other modules to constants
class ADDON:
    _bl_info = None
    _bl_name = None
    _bl_loaded = False
    mod_name = __name__
    mod_name_prefs = mod_name.split(".")[0]

    panel_cat = "Dev"

def getPrefs() -> "MW_prefs":
    """ Get addon preferences from blender """
    return bpy.context.preferences.addons[MW_prefs.bl_idname].preferences

# OPT:: maybe direclty an access to it instead of getter? need some setup per module to avoid parsing before register
prefs = None

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

    #debug
    prefs_PT_meta_show_tmpDebug: props.BoolProperty(
        name="Show debug...", description="WIP: Show some debug stuff",
        default=True,
    )

    #-------------------------------------------------------------------

    # TODO:: move to common place + also properties utils -> use a sub property group?
    # IDEA:: add .to filter or something to idicate match only the beginning
    class names:
        original = "original"
        original_copy = original+"_0_"
        original_convex = original+"_1_convex"
        original_dissolve = original+"_2_dissolve"

        source = "source"
        source_points = source+"_points"
        source_wallsBB = source+"_wallsBB"

        shards = "shards"

        # OPT:: too much redundant "shards.."
        links = "Links"
        links_toWalls = links+"_toWall"
        links_perCell = links+"_perCell"
        links_group = "L"

        # OPT:: dynamic depending on number of cells
        child_idFormat = "03"

        @staticmethod
        def get_IdFormated(idx:int):
            """ Pad with a certain amount of zeroes to achieve a correct lexicographic order """
            return f"{{:{MW_prefs.names.child_idFormat}}}".format(idx)

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

    gen_PT_meta_show_visuals: props.BoolProperty(
        name="Show visuals...", description="Tweak visual elements",
        default=True,
    )
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
    # XXX:: fix storage problems callbacks?

    def prefs_links_undoPurge_update(self, context):
        if self.prefs_links_undoPurge:
            handlers.callback_undo_actions.append(LinkStorage.purgeLinks_callback)
            LinkStorage.purgeLinks()
        else:
            handlers.callback_undo_actions.remove(LinkStorage.purgeLinks_callback)

    nbl_prefs_links_undoPurge_default = False
    prefs_links_undoPurge: props.BoolProperty(
        name="purge", description="Keep purging on undo",
        default=nbl_prefs_links_undoPurge_default,
        update=prefs_links_undoPurge_update,
        #update= lambda self, context: MW_prefs.LinkStorage.purgeLinks()
    )

    #-------------------------------------------------------------------

    gen_duplicate_OT_hidePrev: props.BoolProperty(
        name="hide", description="Hide the original fractured object after duplication",
        default=True,
    )

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
    #debug

    dm_PT_meta_show_tmpDebug: props.BoolProperty(
        name="Show debug...", description="WIP: Show some debug stuff",
        default=True,
    )
    dm_PT_orphans_collection: props.StringProperty(
        name="", description="E.g. meshes, curves, etc",
        default="meshes, curves",
    )


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_prefs,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    # Class declaration cannot be dynamic, so could assert afterwards
    #assert(MW_prefs.bl_idname == ADDON._bl_info["name"])
    assert(MW_prefs.bl_idname == ADDON._bl_name)

    # NOTE:: sync with default state? cannot add static attrs to the addonprefs?
    if MW_prefs.nbl_prefs_links_undoPurge_default:
        handlers.callback_undo_actions.append(LinkStorage.purgeLinks_callback)
    handlers.callback_loadFile_actions.append(LinkStorage.purgeLinks_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    # OPT:: some global init that has acess to bpy context after reloading extensions? e.g. open draw debug panel? not
    global prefs
    prefs = getPrefs()

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    # might end up set or not -> could access prefs and check
    handlers.callback_undo_actions.removeCheck(LinkStorage.purgeLinks_callback)
    handlers.callback_loadFile_actions.remove(LinkStorage.purgeLinks_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})