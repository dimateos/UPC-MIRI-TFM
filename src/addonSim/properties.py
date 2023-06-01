import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs

from . import handlers
from . import utils
from .utils_dev import DEV


# OPT:: comment some sections
#-------------------------------------------------------------------

class MW_gen_cfg(types.PropertyGroup):

    meta_type: props.EnumProperty(
        name="Type", description="Meta type added to the object to control some logic",
        items=(
            ('NONE', "No fracture", "No fracture generated"),
            ('ROOT', "Root object", "Root object holding the fracture"),
            ('CHILD', "Child object", "Child object part of the fracture"),
        ),
        options={'ENUM_FLAG'},
        default={'NONE'},
    )

    @staticmethod
    def isRoot(obj: types.Object) -> bool:
        return "ROOT" in obj.mw_gen.meta_type
    @staticmethod
    def isChild(obj: types.Object) -> bool:
        return "CHILD" in obj.mw_gen.meta_type

    @staticmethod
    def hasRoot(obj: types.Object) -> bool:
        """ Quick check if the object is part of a fracture """
        #DEV.log_msg(f"hasRoot check: {obj.name} -> {obj.mw_gen.meta_type}", {"REC", "CFG"})
        return "NONE" not in obj.mw_gen.meta_type

    # OPT:: should really try to acces the parent direclty -> but careful with rna of deleted...
    # OPT:: too much used around in poll functions, performance hit? use a callback to be used on selected object? +also show name of selected etc
    @staticmethod
    def getRoot(obj: types.Object) -> tuple[types.Object, "MW_gen_cfg"]:
        """ Retrieve the root object holding the config (MW_gen_cfg forward declared)"""
        #DEV.log_msg(f"getRoot search: {obj.name} -> {obj.mw_gen.meta_type}", {"REC", "CFG"})
        if "NONE" in obj.mw_gen.meta_type:
            return obj, None

        try:
            obj_chain = obj
            while "CHILD" in obj_chain.mw_gen.meta_type:
                obj_chain = obj_chain.parent

            # OPT:: check the root is actually root: could happen if an object is copy pasted
            if "ROOT" not in obj_chain.mw_gen.meta_type: raise ValueError("Chain ended with no root")
            #DEV.log_msg(f"getRoot chain end: {obj_chain.name}", {"RET", "CFG"})
            return obj_chain, obj_chain.mw_gen

        # the parent was removed
        except AttributeError:
            DEV.log_msg(f"getRoot chain broke: {obj.name} -> no rec parent", {"ERROR", "CFG"})
            return obj, None
        # the parent was not root
        except ValueError:
            DEV.log_msg(f"getRoot chain broke: {obj_chain.name} -> not root ({obj_chain.mw_gen.meta_type})", {"ERROR", "CFG"})
            return obj, None

    @staticmethod
    def getSceneRoots(scene: types.Scene) -> list[types.Object]:
        roots = [ obj for obj in scene.objects if MW_gen_cfg.isRoot(obj) ]
        return roots

    @staticmethod
    def setMetaType(obj: types.Object, type: set[str], skipParent = False, childrenRec = True):
        """ Set the property to the object and all its children (dictionary ies copied, not referenced)
            # NOTE:: acessing obj children is O(len(bpy.data.objects)), so just call it on the root again
        """
        if not skipParent:
            obj.mw_gen.meta_type = type.copy()

        toSet = obj.children_recursive if childrenRec else obj.children
        #DEV.log_msg(f"Setting {type} to {len(toSet)} objects", {"CFG"})
        for child in toSet:
            child.mw_gen.meta_type = type.copy()

    #-------------------------------------------------------------------
    #callbacks

    # OPT:: unset on reload, could have a flag and let the panel update it -> cannot be done from addon register
    nbl_selectedRoot_currentCFG = None
    nbl_selectedRoot_currentOBJ = None

    @classmethod
    def hasSelectedRoot(cls) -> bool:
        return cls.nbl_selectedRoot_currentOBJ and cls.nbl_selectedRoot_currentCFG

    @classmethod
    def getSelectedRoot(cls) -> tuple[types.Object, "MW_gen_cfg"]:
        return cls.nbl_selectedRoot_currentOBJ, cls.nbl_selectedRoot_currentCFG
    @classmethod
    def getSelectedRoot_obj(cls) -> types.Object:
        return cls.nbl_selectedRoot_currentOBJ
    @classmethod
    def getSelectedRoot_cfg(cls) -> "MW_gen_cfg":
        return cls.nbl_selectedRoot_currentCFG


    @classmethod
    def setSelectedRoot(cls, selected):
        # OPT:: multi-selection / root?
        if selected: cls.nbl_selectedRoot_currentOBJ, cls.nbl_selectedRoot_currentCFG = cls.getRoot(selected[-1])
        else: cls.nbl_selectedRoot_currentOBJ, cls.nbl_selectedRoot_currentCFG = None,None

    # trigger new root on selection
    @classmethod
    def setSelectedRoot_callback(cls, _scene_=None, _selected_=None):
        cls.setSelectedRoot(_selected_)

    @classmethod
    def resetSelectedRoot(cls):
        cls.nbl_selectedRoot_currentOBJ, cls.nbl_selectedRoot_currentCFG = None, None


    @classmethod
    def sanitizeSelectedRoot(cls):
        if utils.needsSanitize_object(cls.nbl_selectedRoot_currentOBJ):
            cls.resetSelectedRoot()

    @classmethod
    def sanitizeSelectedRoot_callback(cls, _scene_=None, _name_selected_=None):
        cls.sanitizeSelectedRoot()

    #-------------------------------------------------------------------

    ptrID_links: props.StringProperty(default="nullptr")

    #def init(self):
    #    self.test_str = "test"

    #    # fracture data preserved on the object
    #    #self.nbl_cont: Container = None
    #    #self.nbl_links: LinkCollection = None

    #test_str: str = "test"
    #test_strProp: props.StringProperty(default="testProp")

    #-------------------------------------------------------------------

    # dynamic source options
    class sourceOptions:
        all=[
            ('VERT_OWN', "Own Verts", "Use own vertices (also set by default when other options are disabled)"),
            ('VERT_CHILD', "Child Verts", "Use child object vertices"),
            ('PARTICLE_OWN', "Own Particles", "All particle systems of the source object"),
            ('PARTICLE_CHILD', "Child Particles", "All particle systems of the child objects"),
            #('PENCIL', "Pencil", "Annotation Grease Pencil (only touching/inside the volume)"),
        ]
        all_keys = [ k[0] for k in all ]
        default_key = 'PARTICLE_CHILD'
        fallback_key = 'VERT_OWN'
        error_key = 'NONE'
        error_option = [ (error_key, "No point found...", f"Options: {all_keys}") ]

    meta_source_enabled: props.EnumProperty(
        name="Source all types",
        items=sourceOptions.all.copy(),
        default={ sourceOptions.fallback_key },
        options={'ENUM_FLAG'},
    )

    def source_dynamic(self, context):
        items = [
            t for t in self.sourceOptions.all
                if t[0] in self.meta_source_enabled
        ]
        if items: return items
        else: return self.sourceOptions.error_option.copy()

    source: props.EnumProperty(
        name="Source", description="Available source from where to retrieve points",
        items=source_dynamic, # default with numberID doesnt seem to work
        options={'ENUM_FLAG'},
    )

    source_limit: props.IntProperty(
        name="Limit points", description="Limit the number of input points, 0 for unlimited",
        default=100, min=0, max=5000,
    )
    source_noise: props.FloatProperty(
        name="RND noise", description="Randomize point distribution",
        default=0.0, min=0.0, max=1.0,
    )
    rnd_seed: props.IntProperty(
        name="RND seed", description="Seed the random generator, -1 to unseed it",
        default=64, min=-1,
    )

    #-------------------------------------------------------------------

    shape_useConvexHull: props.BoolProperty(
        name="WIP: Convex hull", description="Apply convex hull op beforehand",
        default=True,
    )
    shape_useWalls: props.BoolProperty(
        name="Wall planes", description="Keep the object faces as container walls (kind of like boolean op)",
        default=True,
    )


    # OPT:: example of having a per instance previous value of a property
    def struct_nameOriginal_update(self, context):
        #if self.struct_nameOriginal_prev == self.struct_nameOriginal: return # prev val is also reset on undo tho
        self.struct_nameOriginal_prev = self.struct_nameOriginal_prevRep
        self.struct_nameOriginal_prevRep = self.struct_nameOriginal
        DEV.log_msg(f"struct_nameOriginal: {self.struct_nameOriginal} - prev: {self.struct_nameOriginal_prev}", {"CALLBACK", "CFG", "PREV"})
    struct_nameOriginal: props.StringProperty(
        update= struct_nameOriginal_update
    )
    struct_nameOriginal_prevRep: props.StringProperty()
    struct_nameOriginal_prev: props.StringProperty()

    struct_namePrefix: props.StringProperty(
        name="Prefix",
        default="MW",
    )

    def get_struct_name(self):
        return f"{self.struct_namePrefix}_{self.struct_nameOriginal}"
    def get_struct_nameNew(self, newName):
        #self.struct_nameOriginal = newName
        return f"{self.struct_namePrefix}_{newName}"

    #-------------------------------------------------------------------
    # NOTE:: now the elements can be properly hidden while the last operator panel is open...
    # IDEA:: use for actually adding to the scene or not

    struct_showShards: props.BoolProperty(
        name="Shards", description="Voronoi cells",
        default=True,
    )

    struct_showLinks: props.BoolProperty(
        name="WIP: Links", description="Voronoi cells links per face",
        default=True,
    )
    struct_showLinks_airLinks: props.BoolProperty(
        name="WIP: Links to walls", description="Voronoi cells links per face to walls",
        default=True,
    )
    struct_showLinks_legacy: props.BoolProperty(
        name="Cell links (centroid)", description="Links from centroids to neigh cells",
        default=False,
    )

    struct_showPoints: props.BoolProperty(
        name="Points", description="The ones used for the cells generation",
        default=True,
    )
    struct_showBB: props.BoolProperty(
        name="BB", description="The extended BB min max points, tobble show bounding box in viewport",
        default=True,
    )
    struct_showOrignal_scene: props.BoolProperty(
        name="Source Obj", description="The original object in the scene",
        default=False,
    )

    struct_showOrignal: props.BoolProperty(
        name="Original", description="The original object backup child",
        default=False,
    )
    struct_showConvex: props.BoolProperty(
        name="Convex", description="The original object convex hull",
        default=False,
    )
    struct_showLow: props.BoolProperty(
        name="WIP: Low", description="The convex hull decimated",
        default=False,
    )

    #-------------------------------------------------------------------
    # IDEA:: update to direclty modify the scene

    def struct_shardScale_update(self, context):
        obj = MW_gen_cfg.getSelectedRoot_obj()
        if not obj: return
        shards = utils.get_child(obj, getPrefs().names.shards)
        utils.scale_objectChildren(shards, self.struct_shardScale)

    struct_shardScale: props.FloatProperty(
        name="Shard scale", description="Reduce some bits to be able to see the links better",
        default=0.9, min=0.25, max=1,
        update=struct_shardScale_update
    )

    # IDEA:: maybe keep attached to faces by having and ID or something? atm momment cannot scale like this need another pivot
    def struct_linksScale_update(self, context):
        obj = MW_gen_cfg.getSelectedRoot_obj()
        if not obj: return
        links = utils.get_child(obj, getPrefs().names.links)
        if links: utils.scale_objectChildren(links, self.struct_linksScale)
        links_Air_Cell = utils.get_child(obj, getPrefs().names.links_air)
        if links_Air_Cell: utils.scale_objectChildren(links_Air_Cell, self.struct_linksScale)


    struct_linksScale: props.FloatProperty(
        name="Links scale", description="Reduce some bits to be able to see the links better",
        default=1, min=0.25, max=3,
        update=struct_linksScale_update
    )

    #-------------------------------------------------------------------

    # NOTE:: inter-spacing for physics is not possible atm
    # IDEA:: could allow negative margins, but then handle 0 when points are on the wall?
    margin_box_bounds: props.FloatProperty(
        name="Margin BB", description="Additional displacement of the box normal planes",
        default=0.05, min=0.001, max=1.0, step=1, precision=3
    )
    margin_face_bounds: props.FloatProperty(
        name="Margin faces", description="Additional displacement of the face normal planes",
        default=0.025, min=0.001, max=1.0, step=1, precision=3
    )

#-------------------------------------------------------------------
# OPT:: maybe split files + some go to prefs + new propGroup to add to scene props_utils instead of prefs
# IDEA:: vis cfg part of each gen and sim, or subpart with another group?
# IDEA:: using animation frame handler to see the simulaion play?
# IDEA:: min -1 for infinite break condition?

class MW_SIM_CONST(types.PropertyGroup):
    steps: props.IntProperty(
        name="Number of iters", description="WIP: atm redo each modification",
        default=1, min=0, max=1000,
    )
    subSteps: props.IntProperty(
        name="Number of propagations per iter", description="WIP: atm redo each modification",
        default=10, min=0, max=100,
    )

    steps_uniformDeg: props.BoolProperty(
        name="Uniform reduction",
        default=False,
    )
    steps_reset: props.BoolProperty(
        name="Reset at start",
        default=True,
    )

    deg: props.FloatProperty(
        name="Degradation", description="WIP: flat reduction",
        default=0.025, min=0.001, max=0.1, step=1, precision=3
    )

    addSeed: props.IntProperty(
        name="Add random seed",
        default=0, min=0, max=100,
    )

#class MW_vis_cfg(types.PropertyGroup):
#    pass


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_cfg,
    MW_SIM_CONST,
    #MW_vis_cfg,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    handlers.callback_selectionChange_actions.append(MW_gen_cfg.setSelectedRoot_callback)
    handlers.callback_loadFile_actions.append(MW_gen_cfg.sanitizeSelectedRoot_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    # appear as part of default object props
    bpy.types.Object.mw_gen = props.PointerProperty(
        type=MW_gen_cfg,
        name="MW_Generation", description="MW generation properties")

    bpy.types.Object.mw_sim = props.PointerProperty(
        type=MW_SIM_CONST,
        name="MW_Simulation", description="MW simulation properties")

    ## WIP maybe visualization stored in scene?
    #bpy.types.Object.mw_vis = props.PointerProperty(
    #    type=MW_vis_cfg,
    #    name="MW_Visualization", description="MW visualization properties")

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    handlers.callback_selectionChange_actions.remove(MW_gen_cfg.setSelectedRoot_callback)
    handlers.callback_loadFile_actions.remove(MW_gen_cfg.sanitizeSelectedRoot_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})