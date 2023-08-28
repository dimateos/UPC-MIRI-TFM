import bpy
import bpy.types as types
import bpy.props as props

from . import handlers

from .utils_dev import DEV

from .properties_utils import Prop_inspector
from .properties_global import MW_global_storage

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
    bl_idname = ADDON.mod_name_prefs
    """ NOTE:: __name__ must be exaclty used for addon prefs, so check when deploying without the addon"""

    def draw(self, context):
        """ Draw in preferences panel"""
        # Careful with circulare dependecies, maybe split the class with draw and props
        from .ui import draw_propsToggle
        draw_propsToggle(self, prefs.prefs_PT_meta_inspector, self.layout)

    #-------------------------------------------------------------------

    prefs_links_undoPurge: props.BoolProperty(
        name="purge", description="Keep purging on undo",
        default=MW_global_storage.undoPurge_default,
        update= lambda self, context: MW_global_storage.undoPurge_callback = self.prefs_links_undoPurge
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
        links = "links"
        links_air = links+"_air"
        links_legacy = links+"_legacy"
        links_group = "L"

        # OPT:: dynamic depending on number of cells
        child_idFormat = "04"

        @staticmethod
        def get_IdFormated(idx:int):
            """ Pad with a certain amount of zeroes to achieve a correct lexicographic order """
            return f"{{:{MW_prefs.names.child_idFormat}}}".format(idx)

    #-------------------------------------------------------------------

    # meta filter for OP props
    prefs_PT_meta_inspector: props.PointerProperty(type=Prop_inspector)
    gen_PT_meta_inspector: props.PointerProperty(type=Prop_inspector)
    vis_PT_meta_inspector: props.PointerProperty(type=Prop_inspector)

    all_PT_meta_show_root: props.BoolProperty(
        name="Root props", description="Show root properties / selected child",
        default=True,
    )

    # TODO:: replace for visual cfg ins
    gen_PT_meta_show_visuals: props.BoolProperty(
        name="Show visuals...", description="Tweak visual elements",
        default=False,
    )

    #-------------------------------------------------------------------

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

    gen_setup_matColors: props.BoolProperty(
        name="WIP: Add shard color mats", description="Materials aded on generation",
        default=False,
    )
    gen_setup_matAlpha: props.FloatProperty(
        name="WIP: Shard mat alpha", description="See the links through",
        default=0.66, min=0.1, max=1
    )

    links_matAlpha: props.BoolProperty(
        name="WIP: Link alpha mod", description="Degrade alpha with life",
        default=False,
    )
    links_smoothShade: props.BoolProperty(
        name="WIP: Link smooth shade",
        default=True,
    )
    links_depth: props.FloatProperty(
        name="WIP: Const link depth", description="Constant link d",
        default=0.15, min=0.01, max=0.4, step=0.05, precision=4
    )
    links_width: props.FloatProperty(
        name="WIP: Link width", description="Max link w",
        default=0.05, min=0.01, max=0.2, step=0.05, precision=4
    )
    links_widthDead: props.FloatProperty(
        name="WIP: Dead link width", description="Min link w",
        default=0.005, min=0.001, max=0.01, step=0.05, precision=4
    )

    links_widthModLife: props.EnumProperty(
        name="WIP: Life affects width",
        items=(
            ('DISABLED', "Disabled", "No effect on width"),
            ('UNIFORM', "Uniform effect", "Uniform effect on width"),
            ('BINARY', "Binary", "Any differece from full life affects drastically"),
        ),
        options={'ENUM_FLAG'},
        default={'BINARY'},
    )

    links_res: props.IntProperty(
        name="WIP: Link res", description="WIP: curve res -> faces",
        default=0, min=-1, max=8,
    )
    links_wallExtraScale: props.FloatProperty(
        name="WIP: Link walls extra", description="WIP: extra scaling",
        default=1.25, min=0.25, max=3,
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

    util_recalc_OT_auto: props.BoolProperty(
        name="auto", description="Recalculate automatically when needed",
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
        default=False,
    )
    dm_PT_orphans_collection: props.StringProperty(
        name="", description="E.g. meshes, mats, curves, etc",
        default="meshes, materials, curves",
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

    for cls in classes:
        bpy.utils.register_class(cls)

    # OPT:: some global init that has acess to bpy context after reloading extensions? e.g. open draw debug panel? not
    global prefs
    prefs = getPrefs()

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})