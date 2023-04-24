import bpy
import bpy.types as types
import bpy.props as props
from mathutils import Vector, Matrix

from . import ui
from . import utils
from . import utils_geo
from . import utils_render
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class Common_OT_StartRefresh(types.Operator):
    """ Common operator class with start/end messages/stats + controlled refresh """

    def __init__(self) -> None:
        super().__init__()
        # to be configured per class / from outside before execution
        self.invoke_log         = True
        self.refresh_log        = True
        self.start_resetStats   = True
        self.start_logEmptyLine = True
        self.start_log          = True
        self.start_logStats     = False
        self.end_logEmptyLine   = True
        self.end_log            = True
        self.end_logStats       = True



    def draw(self, context: types.Context):
        """ Runs about 2 times after execution / panel open / mouse over moved """
        #super().draw(context)
        ui.draw_refresh(self, self.layout)

    def invoke(self, context, event):
        """ Runs only once on operator call """
        if self.refresh_log:
            DEV.log_msg("invoke", {'OP_FLOW'})

        # refresh at least once
        self.meta_refresh = True
        return self.execute(context)
        #return super().invoke(context, event)

    def execute(self, context: types.Context):
        """ Runs once and then after every property edit in the edit last action panel """
        # sample flow to be overwritten:
        self.start_op()

        if self.checkRefresh_return():
            return self.end_op_refresh()

        error = False
        if error:
            return self.end_op_error()

        return self.end_op()

    #-------------------------------------------------------------------
    # common refresh handling

    meta_refresh: props.BoolProperty(
        name="Refresh", description="Refresh once on click",
        default=False,
    )
    meta_auto_refresh: props.BoolProperty(
        name="Auto-Refresh", description="Automatic refresh",
        default=True,
    )

    def checkRefresh_cancel(self):
        if self.refresh_log:
            DEV.log_msg(f"execute auto_refresh:{self.meta_auto_refresh} refresh:{self.meta_refresh}", {'OP_FLOW'})

        # cancel op exec
        if not self.meta_refresh and not self.meta_auto_refresh:
            return True
        self.meta_refresh = False
        return False

    #-------------------------------------------------------------------
    # common log+stats

    def start_op(self, msg="",):
        stats = getStats()
        if self.start_resetStats: stats.reset()
        #stats.testStats()

        if self.start_logEmptyLine: print()
        if self.start_log:
            if not msg: msg= f"{self.bl_label}"
            DEV.log_msg(f"Op START: {msg} ({self.bl_idname})", {'OP_FLOW'})

        if self.start_logStats: stats.logDt(f"timing: ({self.bl_idname})...")

    def end_op(self, msg="", skip=False):
        if self.end_log:
            if not msg: msg= f"{self.bl_label}"
            DEV.log_msg(f"Op END: {msg} ({self.bl_idname})", {'OP_FLOW'})
        if self.end_logEmptyLine: print()

        if self.end_logStats: getStats().logT(f"finished: ({self.bl_idname})...")
        return {"FINISHED"} if not skip else {'PASS_THROUGH'}

    def end_op_error(self, msg = "", skip=False):
        # blender pop up that shows the message
        self.report({'ERROR'}, f"Op FAILED: {msg}")
        self.end_op(msg, skip)

    def end_op_refresh(self, msg = "", skip=True):
        self.end_op(msg, skip)

#-------------------------------------------------------------------

class MW_util_indices_OT_(types.Operator):
    bl_idname = "mw.util_indices"
    bl_label = "Spawn mesh indices"
    bl_options = {"PRESET", 'REGISTER', 'UNDO'}
    bl_description = "Spawn named objects at mesh data indices positons"

    class CONST_NAMES:
        empty = "spawn_Indices"
        verts = "verts_Indices"
        edges = "edges_Indices"
        faces = "faces_Indices"

    # toggles and scale per data
    _prop_showName = props.BoolProperty(name="name", description="Toggle viewport vis of names", default=False)
    _prop_scale = props.FloatProperty(name="s", default=0.25, min=0.01, max=2.0)
    verts_gen: props.BoolProperty( name="Verts (octa)", default=True)
    verts_name: _prop_showName
    verts_scale: _prop_scale
    edges_gen: props.BoolProperty( name="Edges (cube)", default=False)
    edges_name: _prop_showName
    edge_scale: _prop_scale
    faces_gen: props.BoolProperty( name="Faces (tetra)", default=True)
    faces_name: _prop_showName
    faces_scale: _prop_scale

    # rendering
    color_alpha: props.FloatProperty(name="color alpha", default=0.5, min=0.1, max=1.0)
    color_useGray: props.BoolProperty( name="grayscale", default=False)
    color_gray: props.FloatProperty(name="white", default=0.5, min=0.0, max=1.0)
    mesh_useShape: props.BoolProperty( name="use mesh shapes", default=True)
    mesh_scale: _prop_scale
    namePrefix: props.StringProperty(
        name="obj prefix", description="Avoid blender adding .001 to repeated objects/meshes",
        default="",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.data

    def invoke(self, context, event):
        # print(self.recursion_chance_select)
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

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
        row = col.row().split(factor=f2)
        row.prop(self, "mesh_useShape")
        row.prop(self, "mesh_scale", text="scale")

        rowsub = col.row()
        rowsub.alignment = "LEFT"
        rowsub.prop(self, "namePrefix")

    def execute(self, context: types.Context):
        getStats().logMsg(f"START: {self.bl_label} ({self.bl_idname})")
        obj = context.active_object
        child_empty = utils.gen_childClean(obj, self.CONST_NAMES.empty, context, None, keepTrans=False)

        # optional grayscale common color mat
        gray3 = utils_render.COLORS.white * self.color_gray
        if self.color_useGray:
            mat_gray = utils_render.get_colorMat(gray3, self.color_alpha)

        if self.verts_gen:
            # verts use a octahedron for rep
            if self.mesh_useShape: mesh = utils_render.SHAPES.get_octahedron(f"{self.namePrefix}.vert")
            else: mesh= None
            scaleV = Vector([self.verts_scale * self.mesh_scale]*3)

            # red colored mat
            if self.color_useGray: mat = mat_gray
            else: mat = utils_render.get_colorMat(utils_render.COLORS.red+gray3, self.color_alpha)

            # spawn as children
            parent = utils.gen_child(child_empty, self.CONST_NAMES.verts, context, None, keepTrans=False)
            for v in obj.data.vertices:
                name = f"{self.namePrefix}.v{v.index}"
                child = utils.gen_child(parent, name, context, mesh, keepTrans=False)
                child.location = v.co
                child.scale = scaleV
                child.active_material = mat
                child.show_name = self.verts_name
                # orient vert out
                v_rot0: Vector = Vector([0,0,1])
                v_rot1: Vector = v.normal
                child.rotation_mode = "QUATERNION"
                child.rotation_quaternion = v_rot0.rotation_difference(v_rot1)

        if self.edges_gen:
            # edges use a cube for rep
            if self.mesh_useShape: mesh = utils_render.SHAPES.get_cuboid(f"{self.namePrefix}.edge")
            else: mesh= None
            scaleV = Vector([self.edge_scale * self.mesh_scale]*3)

            # red colored mat
            if self.color_useGray: mat = mat_gray
            else: mat = utils_render.get_colorMat(utils_render.COLORS.green+gray3, self.color_alpha)

            # spawn as children
            parent = utils.gen_child(child_empty, self.CONST_NAMES.edges, context, None, keepTrans=False)
            for e in obj.data.edges:
                name = f"{self.namePrefix}.e{e.index}"
                child = utils.gen_child(parent, name, context, mesh, keepTrans=False)
                child.location = utils_geo.edge_center(obj.data, e)
                child.scale = scaleV
                child.active_material = mat
                child.show_name = self.edges_name
                # orient edge along
                v_rot0: Vector = Vector([0,0,1])
                v_rot1: Vector = utils_geo.edge_dir(obj.data, e)
                child.rotation_mode = "QUATERNION"
                child.rotation_quaternion = v_rot0.rotation_difference(v_rot1)

        if self.faces_gen:
            # faces use a tetrahedron for rep
            if self.mesh_useShape: mesh = utils_render.SHAPES.get_tetrahedron(f"{self.namePrefix}.face")
            else: mesh= None
            scaleV = Vector([self.faces_scale * self.mesh_scale]*3)

            # red colored mat
            if self.color_useGray: mat = mat_gray
            else: mat = utils_render.get_colorMat(utils_render.COLORS.blue+gray3, self.color_alpha)

            # spawn as children
            parent = utils.gen_child(child_empty, self.CONST_NAMES.faces, context, None, keepTrans=False)
            for f in obj.data.polygons:
                name = f"{self.namePrefix}.f{f.index}"
                child = utils.gen_child(parent, name, context, mesh, keepTrans=False)
                child.location = f.center + f.normal*0.1*scaleV[0]
                child.scale = scaleV
                child.active_material = mat
                child.show_name = self.faces_name
                # orient face out
                v_rot0: Vector = Vector([0,0,1])
                v_rot1: Vector = f.normal
                child.rotation_mode = "QUATERNION"
                child.rotation_quaternion = v_rot0.rotation_difference(v_rot1)


        getStats().logT(f"END: {self.bl_label} ({self.bl_idname})")
        return {'FINISHED'}


class MW_util_deleteIndices_OT_(types.Operator):
    bl_idname = "mw.util_indices_delete"
    bl_label = "del"
    bl_options = {'INTERNAL', 'UNDO'}
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."
    _obj:types.Object = None

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False

        obj = utils.get_child(context.active_object, MW_util_indices_OT_.CONST_NAMES.empty)
        MW_util_deleteIndices_OT_._obj = obj
        return obj

    def execute(self, context: types.Context):
        getStats().logMsg(f"START: {self.bl_label} ({self.bl_idname})")
        obj = MW_util_deleteIndices_OT_._obj
        utils.delete_objectRec(obj, logAmount=True)

        # UNDO as part of bl_options will cancel any edit last operation pop up
        getStats().logMsg(f"END: {self.bl_label} ({self.bl_idname})")
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

op_util_classes = [
    MW_util_indices_OT_,
    MW_util_deleteIndices_OT_,
    MW_info_data_OT_,
    MW_info_API_OT_,
    MW_info_matrices_OT_
]