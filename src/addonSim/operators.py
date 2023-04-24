import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import mw_setup
from . import mw_calc
from .mw_links import Links, Link

from . import ui
from . import utils
from . import utils_render
from .utils_cfg import copyProps
from .utils_dev import DEV
from .stats import getStats

from mathutils import Vector
from tess import Container, Cell


#-------------------------------------------------------------------

class MW_gen_OT_(types.Operator):
    bl_idname = "mw.gen"
    bl_label = "Fracture generation"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}
    bl_description = "Fracture generation using voro++"

    cfg: props.PointerProperty(type=MW_gen_cfg)

    def draw(self, context: types.Context):
        ui.draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        """ Runs only once on operator call """
        DEV.log_msg("invoke", {'OP_FLOW'})

        # refresh at least once
        self.cfg.meta_refresh = True
        # avoid last stored operation overide
        self.cfg.meta_type = {"NONE"}

        return self.execute(context)


    def __init__(self) -> None:
        super().__init__()

    def start_op(self, msg = ""):
        getStats().reset()
        #getStats().testStats()
        print()
        DEV.log_msg(msg, {'SETUP'})
        DEV.log_msg(f"execute auto_refresh:{self.cfg.meta_auto_refresh} refresh:{self.cfg.meta_refresh}", {'OP_FLOW'})

    def end_op(self, msg = "", skip=False):
        DEV.log_msg(f"END: {msg}", {'OP_FLOW'})
        getStats().logT("finished execution")
        print()
        return {"FINISHED"} if not skip else {'PASS_THROUGH'}

    def end_op_error(self, msg = "", skip=False):
        self.report({'ERROR'}, f"Operation failed: {msg}")
        self.end_op(msg, skip)

    # IDEA:: changelog / todo file to take notes there instead of all in the code?

    # OPT::  GEN: more error handling of user deletion of intermediate objects?
    # OPT:: automatically add particles -> most interesting method...
    # IDEA:: GEN: support for non meshes (e.g. curves)
    # IDEA:: GEN: disabled pencil too, should check points are close enugh/inside
    # IDEA:: GEN: atm only a single selected object + spawning direclty on the scene collection
    # IDEA:: GEN: recursiveness of shards?
    # NOTE:: GEN: avoid convex hull from voro++
    # OPT:: RENDER: interior handle for materials

    # IDEA:: SIM: shrink here or as part of sim, e.g. smoothing? -> support physics interspace
    # IDEA:: SIM: add mass add rigid body proportional to volume? from voro++?

    def execute(self, context: types.Context):
        """ Runs once and then after every property edit in the edit last action panel """
        self.start_op("START: fracture OP")

        # TODO:: store cont across simulations in the object or info from it
        # TODO:: run again more smartly, like detect no need for changes (e.g. name change or prefs debug show) -> compare both props, or use prop update func self ref?
        # XXX:: particles are in world position?
        # XXX:: refresh is slow, maybe related to other ui doing recursive access to root?? maybe panel with ok before?
        # OPT:: separate simulation and scene generation: option to no store inter meshes
        # OPT:: adding many objects to the scene takes most of the time -> single global mesh?
        # OPT:: avoid recursion with pointer to parent instead of search by name
        # IDEA:: decimate before/after convex, test perf?

        # Handle refreshing
        if not self.cfg.meta_refresh and not self.cfg.meta_auto_refresh:
            return self.end_op("PASS_THROUGH no refresh", skip=True)
        self.cfg.meta_refresh = False

        # TODO:: divide execute in functions?
        # TODO:: make timing stats global and time from the methods not here

        # Need to copy the properties from the object if its already a fracture
        obj, cfg = utils.cfg_getRoot(context.active_object)
        getStats().logDt("retrieved root object")

        # Selected object not fractured
        if not cfg:
            DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
            cfg: MW_gen_cfg = self.cfg

            # TODO:: convex hull triangulates the faces... just decimate pls
            obj, obj_toFrac = mw_setup.gen_copyOriginal(obj, cfg, context)
            if cfg.shape_useConvexHull:
                obj_toFrac = mw_setup.gen_copyConvex(obj, obj_toFrac, cfg, context)

        # Copy the config to the operator once
        else:
            if "NONE" in self.cfg.meta_type:
                DEV.log_msg("cfg found: copying props to OP", {'SETUP'})
                copyProps(cfg, self.cfg)
                return self.end_op("PASS_THROUGH init copy of props")

            else:
                DEV.log_msg("cfg found: getting toFrac child", {'SETUP'})
                cfg: MW_gen_cfg = self.cfg

                if cfg.shape_useConvexHull:
                    name_toFrac = mw_setup.CONST_NAMES.original_convex
                else:
                    name_toFrac = f"{mw_setup.CONST_NAMES.original}{cfg.struct_nameOriginal}"

                obj_toFrac = utils.get_child(obj, name_toFrac)
                getStats().logDt("retrieved toFrac object")


        DEV.log_msg("Start calc points", {'SETUP'})
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed) # seed common random gen

        # Get the points and transform to local space when needed
        mw_calc.detect_points_from_object(obj_toFrac, cfg, context)
        points = mw_calc.get_points_from_object_fallback(obj_toFrac, cfg, context)
        if not points:
            return self.end_op_error("found no points...")

        # Get more data
        bb, bb_radius = utils.get_bb_radius(obj_toFrac, cfg.margin_box_bounds)
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []

        # Limit and rnd a bit the points and add them to the scene
        mw_calc.points_transformCfg(points, cfg, bb_radius)


        # Calc voronoi
        DEV.log_msg("Start calc cont", {'SETUP'})
        cont = mw_calc.cont_fromPoints(points, bb, faces4D)

        obj_shards = mw_setup.gen_shardsEmpty(obj, cfg, context)
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, context)

        # XXX:: there is a hard limit in the number of voro++ walls
        #/** The maximum size for the wall pointer array. */
        #const int max_wall_size=2048;

        DEV.log_msg("Start calc links", {'SETUP'})
        links = Links(cont, obj_shards)
        # NOTE:: links better generated from map isntead of cont
        obj_links = mw_setup.gen_linksEmpty(obj, cfg, context)
        mw_setup.gen_linksObjects(obj_links, cont, cfg, context)



        DEV.log_msg("Do some more scene setup", {'SETUP'})
        # Finish scene setup and select after optional renaming
        mw_setup.gen_renaming(obj, cfg, context)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        #context.active_object = obj
        getStats().logDt("renamed and selected")

        mw_setup.gen_pointsObject(obj, points, cfg, context)
        mw_setup.gen_boundsObject(obj, bb, cfg, context)

        # Add edited cfg to the object
        copyProps(self.cfg, obj.mw_gen)
        return self.end_op("completed...")


#-------------------------------------------------------------------

class MW_util_delete_OT_(types.Operator):
    bl_idname = "mw.util_delete"
    bl_label = "Delete fracture object"
    bl_options = {'INTERNAL', 'UNDO'}
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."
    _obj, _cfg = None, None

    @classmethod
    def poll(cls, context):
        obj, cfg = utils.cfg_getRoot(context.active_object)
        MW_util_delete_OT_._obj, MW_util_delete_OT_._cfg = obj, cfg
        return (obj and cfg)

    def execute(self, context: types.Context):
        obj, cfg = MW_util_delete_OT_._obj, MW_util_delete_OT_._cfg
        prefs = getPrefs()

        # optionally hide
        if (prefs.OT_util_delete_unhide):
            obj_original = utils.get_object_fromScene(context.scene, cfg.struct_nameOriginal)
            obj_original.hide_set(False)

        utils.delete_objectRec(obj, logAmount=True)

        # UNDO as part of bl_options will cancel any edit last operation pop up
        getStats().logDt("END: " + self.bl_label)
        return {'FINISHED'}

#-------------------------------------------------------------------

class MW_util_indices_OT_(types.Operator):
    bl_idname = "mw.util_indices"
    bl_label = "Spawn mesh indices"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Spawn named objects at mesh data indices positons"

    class CONST_NAMES:
        empty = "spawn_Indices"
        verts = "verts_Indices"
        edges = "edges_Indices"
        faces = "faces_Indices"

    # toggles and scale per data
    _prop_showName = props.BoolProperty(name="name", description="Toggle viewport vis of names", default=True)
    _prop_scale = props.FloatProperty(name="s", default=0.3, min=0.01, max=2.0)
    verts_gen: props.BoolProperty( name="Verts (octa)", default=True)
    verts_name: _prop_showName
    verts_scale: _prop_scale
    edges_gen: props.BoolProperty( name="Edges (cube)", default=True)
    edges_name: _prop_showName
    edge_scale: _prop_scale
    faces_gen: props.BoolProperty( name="Faces (tetra)", default=True)
    faces_name: _prop_showName
    faces_scale: _prop_scale

    # basic color
    color_alpha: props.FloatProperty(name="color alpha", default=0.66, min=0.1, max=1.0)
    color_useGray: props.BoolProperty( name="grayscale", default=False)
    color_gray: props.FloatProperty(name="white", default=0.66, min=0.0, max=1.0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.data

    #def invoke(self, context, event):
    #    # print(self.recursion_chance_select)
    #    wm = context.window_manager
    #    return wm.invoke_props_dialog(self)

    def draw(self, context: types.Context):
        col = self.layout.column()
        col.label(text=f"[Overlay>Text info]: see names", icon="QUESTION")
        f1 = 0.5

        row = col.row().split(factor=f1)
        row.prop(self, "verts_gen")
        row.prop(self, "verts_name")
        row.prop(self, "verts_scale")
        row = col.row().split(factor=f1)
        row.prop(self, "edges_gen")
        row.prop(self, "edges_name")
        row.prop(self, "edge_scale")
        row = col.row().split(factor=f1)
        row.prop(self, "faces_gen")
        row.prop(self, "faces_name")
        row.prop(self, "faces_scale")

        f2 = 0.5
        col.prop(self, "color_alpha")
        row = col.row().split(factor=f2)
        row.prop(self, "color_useGray")
        row.prop(self, "color_gray")

    def execute(self, context: types.Context):
        obj = context.active_object
        mesh = obj.data
        child_empty = utils.gen_childClean(obj, self.CONST_NAMES.empty, context, None, keepTrans=False)

        # optional grayscale common color mat
        if self.color_useGray:
            mat_gray = utils_render.get_colorMat(utils_render.COLORS.white * self.color_gray, self.color_alpha)

        if self.verts_gen:
            # verts use a octahedron for rep
            verts_octa = [
                Vector((0, 0, 1)),
                Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), Vector((0, -1, 0)),
                Vector((0, 0, -1)),
            ]
            faces_octa = [
                [0,1,2], [0,2,3], [0,3,4], [0,4,1],
                [5,2,1], [5,3,2], [5,4,3], [5,1,4],
            ]
            mesh_octa = bpy.data.meshes.new("vert_octa")
            mesh_octa.from_pydata(vertices=verts_octa, edges=[], faces=faces_octa)
            scaleV = Vector([self.verts_scale]*3)

            # red colored mat
            if self.color_useGray: mat_octa = mat_gray
            else: mat_octa = utils_render.get_colorMat(utils_render.COLORS.red, self.color_alpha)

            # spawn as children
            child_verts = utils.gen_child(child_empty, self.CONST_NAMES.verts, context, None, keepTrans=False)
            for v in mesh.vertices:
                name = f"v{v.index}"
                child = utils.gen_child(child_verts, name, context, mesh_octa, keepTrans=False)
                child.location = v.co
                child.scale = scaleV
                child.active_material = mat_octa
                child.show_name = self.verts_name


        #edges = [e for e in mesh.edges]
        #faces = [f for f in mesh.polygons]

        getStats().logDt("END: " + self.bl_label)
        return {'FINISHED'}

#-------------------------------------------------------------------

class MW_info_data_OT_(types.Operator):
    bl_idname = "mw.info_data"
    bl_label = "Print mesh data"
    bl_options = {'INTERNAL'}
    bl_description = "DEBUG print in the console some mesh data etc"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return (obj and obj.type == 'MESH')

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        from . import info_mesh
        info_mesh.desc_mesh_data(obj.data)
        return {'FINISHED'}

class MW_info_API_OT_(types.Operator):
    bl_idname = "mw.info_api"
    bl_label = "Print mesh API"
    bl_options = {'INTERNAL'}
    bl_description = "DEBUG print in the console some mesh API etc"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return (obj and obj.type == 'MESH')

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        from . import info_mesh
        info_mesh.desc_mesh_inspect(obj.data)
        return {'FINISHED'}

class MW_info_matrices_OT_(types.Operator):
    bl_idname = "mw.info_matrices"
    bl_label = "Print obj matrices"
    bl_options = {'INTERNAL'}
    bl_description = "DEBUG print in the console the matrices etc"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        utils.trans_printMatrices(obj)
        return {'FINISHED'}

#-------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
    MW_util_delete_OT_,
    MW_util_indices_OT_,
    MW_info_data_OT_,
    MW_info_API_OT_,
    MW_info_matrices_OT_
)

register, unregister = bpy.utils.register_classes_factory(classes)
