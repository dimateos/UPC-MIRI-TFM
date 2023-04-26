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


# OPT:: add operators to search bars
#-------------------------------------------------------------------

class _StartRefresh_OT(types.Operator):
    """ Common operator class with start/end messages/stats + controlled refresh """
    bl_idname = "__to_override__"
    """ Op bl_idname must be undercase and one . (and only one)"""

    bl_options = {'INTERNAL'}
    """ Op bl_options INTERNAL supposedly hides the operator from search"""

    def __init__(self) -> None:
        super().__init__()
        # to be configured per class / from outside before execution
        self.invoke_log         = False
        self.refresh_log        = False
        self.start_resetStats   = True
        self.start_logEmptyLine = True
        self.start_log          = True
        self.start_logStats     = False
        self.end_logEmptyLine   = True
        self.end_log            = False
        self.end_logStats       = True

    #-------------------------------------------------------------------
    # common flow

    def draw(self, context: types.Context):
        """ Runs about 2 times after execution / panel open / mouse over moved """
        #super().draw(context)
        ui.draw_refresh(self, self.layout)

    def invoke(self, context, event):
        """ Runs only once on operator call """
        if self.invoke_log:
            DEV.log_msg(f"invoke ({self.bl_idname})", {'OP_FLOW'})

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
        """ Checks and updates auto/refresh state, returns True when there is no need to continue exec """
        if self.refresh_log:
            DEV.log_msg(f"execute auto_refresh:{self.meta_auto_refresh} refresh:{self.meta_refresh}", {'OP_FLOW'})

        # cancel op exec
        if not self.meta_refresh and not self.meta_auto_refresh:
            return True
        self.meta_refresh = False
        return False

    #-------------------------------------------------------------------
    # common log+stats

    def start_op(self, msg=""):
        """ Default exit flow at the start of execution """
        stats = getStats()
        if self.start_resetStats: stats.reset()
        #stats.testStats()
        if self.start_logEmptyLine: print()

        if self.start_log:
            if not msg: msg= f"{self.bl_label}"
            DEV.log_msg(f"Op START: {msg} ({self.bl_idname})", {'OP_FLOW'})

        if self.start_logStats: stats.logDt(f"timing: ({self.bl_idname})...")

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ Default exit flow at the end of execution """
        if self.end_log:
            if not msg: msg= f"{self.bl_label}"
            DEV.log_msg(f"Op END: {msg} ({self.bl_idname})", {'OP_FLOW'})

        if self.end_logStats and not skipLog:
            getStats().logT(f"finished: ({self.bl_idname})...")

        if self.end_logEmptyLine: print()
        return {"FINISHED"} if not retPass else {'PASS_THROUGH'}

    def end_op_error(self, msg = "", skipLog=False, retPass=False):
        """ Default exit flow after an error """
        self.logReport(f"Op FAILED: {msg}", {'ERROR'})
        if not msg: msg= f"failed execution"
        return self.end_op(msg, skipLog, retPass)

    def end_op_refresh(self, msg = "", skipLog=True, retPass=True):
        """ Default exit flow after a cancelled refresh """
        if not msg: msg= f"cancel execution (refresh)"
        return self.end_op(msg, skipLog, retPass)

    def logReport(self, msg, rtype = {'WARNING'}):
        """ blender rtype of kind INFO, WARNING or ERROR"""
        # check valid blender type
        if rtype & { "INFO", "WARNING", "ERROR" } == {}:
            DEV.log_msg(f"{msg} (report-FAIL)", rtype)

        else:
            # regular log too
            DEV.log_msg(f"{msg} (report)", rtype)
            # blender pop up that shows the message
            self.report(rtype, f"{msg}")


#-------------------------------------------------------------------

class Util_SpawnIndices_OT(_StartRefresh_OT):
    bl_idname = "dm.util_spawn_indices"
    bl_label = "Spawn mesh indices"
    bl_description = "Spawn named objects at mesh data indices positons"

    # REGISTER + UNDO pops the edit last op window
    bl_options = {"PRESET", 'REGISTER', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.start_resetStats = True

    def draw(self, context: types.Context):
        super().draw(context)
        self.draw_menu()

    #-------------------------------------------------------------------

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

    def draw_menu(self):
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

    #-------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.data

    def execute(self, context: types.Context):
        self.start_op()
        cancel = self.checkRefresh_cancel()
        if cancel: return self.end_op_refresh()

        obj = context.active_object
        child_empty = utils.gen_childClean(obj, self.CONST_NAMES.empty, context, None, keepTrans=False)

        # optional grayscale common color mat
        gray3 = utils_render.COLORS.white * self.color_gray
        if self.color_useGray:
            mat_gray = utils_render.get_colorMat(gray3, self.color_alpha)

        # IDEA:: add more info as suffix + rename after delete so no .001 + also applied to some setup

        if self.verts_gen:
            # verts use a red octahedron for rep
            scaleV = Vector([self.verts_scale * self.mesh_scale]*3)
            if self.mesh_useShape:
                mesh = utils_render.SHAPES.get_octahedron(f"{self.namePrefix}.vert")
                if self.color_useGray: mat = mat_gray
                else: mat = utils_render.get_colorMat(utils_render.COLORS.red+gray3, self.color_alpha)
            else:
                mesh= None
                mat = None

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
            # edges use a green cuboid  for rep
            scaleV = Vector([self.edge_scale * self.mesh_scale]*3)
            if self.mesh_useShape:
                mesh = utils_render.SHAPES.get_cuboid(f"{self.namePrefix}.edge")
                if self.color_useGray: mat = mat_gray
                else: mat = utils_render.get_colorMat(utils_render.COLORS.green+gray3, self.color_alpha)
            else:
                mesh= None
                mat = None

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
            # faces use a blue tetrahedron for rep
            scaleV = Vector([self.faces_scale * self.mesh_scale]*3)
            if self.mesh_useShape:
                mesh = utils_render.SHAPES.get_tetrahedron(f"{self.namePrefix}.face")
                if self.color_useGray: mat = mat_gray
                else: mat = utils_render.get_colorMat(utils_render.COLORS.blue+gray3, self.color_alpha)
            else:
                mesh= None
                mat = None

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

        return self.end_op()


class Util_deleteIndices_OT(_StartRefresh_OT):
    bl_idname = "dm.util_delete_indices"
    bl_label = "del"
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}
    _obj:types.Object = None

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.start_resetStats = False

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False

        obj = utils.get_child(context.active_object, Util_SpawnIndices_OT.CONST_NAMES.empty)
        Util_deleteIndices_OT._obj = obj
        return obj

    def execute(self, context: types.Context):
        self.start_op()
        obj = Util_deleteIndices_OT._obj
        utils.delete_objectRec(obj, logAmount=True)
        return self.end_op()

#-------------------------------------------------------------------

class Info_PrintData_OT(types.Operator):
    bl_idname = "dm.info_print_data"
    bl_label = "Print mesh data"
    bl_description = "DEBUG print in the console some mesh data etc"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return (obj and obj.type == 'MESH')

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        from . import info_mesh
        info_mesh.desc_mesh_data(obj.data)
        return {'FINISHED'}

class Info_PrintAPI_OT(types.Operator):
    bl_idname = "dm.info_print_api"
    bl_label = "Print mesh API"
    bl_description = "DEBUG print in the console some mesh API etc"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return (obj and obj.type == 'MESH')

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        from . import info_mesh
        info_mesh.desc_mesh_inspect(obj.data)
        return {'FINISHED'}

class Info_PrintMatrices_OT(types.Operator):
    bl_idname = "dm.info_print_matrices"
    bl_label = "Print obj matrices"
    bl_description = "DEBUG print in the console the matrices etc"
    bl_options = {'INTERNAL'}

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

util_classes_op = [
    Util_SpawnIndices_OT,
    Util_deleteIndices_OT,
    Info_PrintData_OT,
    Info_PrintAPI_OT,
    Info_PrintMatrices_OT
]