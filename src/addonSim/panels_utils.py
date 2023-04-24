import bpy
import bpy.types as types
import bpy.props as props

from . import operators_utils as ops_util

from . import ui
from . import utils
from .utils_dev import DEV


PANEL_CATEGORY = "Dev"
PANEL_INFO_NOTIFY_NO_SELECTED = False


#-------------------------------------------------------------------

class Info_Inpect_PT(types.Panel):
    bl_category = PANEL_CATEGORY
    bl_label = "MW_info"
    bl_idname = "MW_PT_info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    #bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    edit_showWorld: props.BoolProperty(
        name="world space", description="Show vertices positions in world space",
        default=False,
    )
    edit_showEdges: props.BoolProperty(
        name="Show edges...", description="Show long list of edges with its key (v1, v2)",
        default=False,
    )
    edit_showFaceCenters: props.BoolProperty(
        name="center position", description="Show face center position instead of vertex indices",
        default=False,
    )


    def draw(self, context):
        if bpy.context.mode == 'OBJECT':
            #DEV.log_msg(f"info OBJECT", {'PT_FLOW'})
            self.draw_objectMode(context)
        elif bpy.context.mode == 'EDIT_MESH':
            #DEV.log_msg(f"info MESH", {'PT_FLOW'})
            self.draw_editMode(context)

    def draw_objectMode(self, context):
        layout = self.layout
        col = layout.column()

        # Something selected, not last active
        if not context.selected_objects:
            if PANEL_INFO_NOTIFY_NO_SELECTED:
                col.label(text="No object selected...", icon="ERROR")
            else:
                col.label(text="...")
            return

        if not context.active_object:
            col.label(text="Selected but removed active?", icon="ERROR")
            return

        obj = context.active_object
        mainCol, mainBox = ui.draw_inspectObject(obj, col)
        mainBox.operator(ops_util.Info_PrintMatrices_OT_.bl_idname, icon="LATTICE_DATA")

        col_rowSplit = col.row().split(factor=0.8)
        col_rowSplit.operator(ops_util.Util_SpawnIndices_OT_.bl_idname, icon="TRACKER")
        col_rowSplit.operator(ops_util.Util_deleteIndices_OT_.bl_idname, icon="CANCEL")

        if obj.type == 'MESH':
            col = layout.column()
            col.operator(ops_util.Info_PrintData_OT_.bl_idname, icon="HELP")
            col.operator(ops_util.Info_PrintAPI_OT_.bl_idname, icon="HELP")

    def draw_editMode(self, context):
        layout = self.layout
        obj = bpy.context.object

        mainCol, mainBox = ui.draw_inspectObject(obj, layout, drawTrans=False)

        col = mainCol.column()
        col.enabled = False
        col.alignment = 'LEFT'
        col.scale_y = 1.2
        col.label(text=f"[toggle Edit/Object]: update", icon="QUESTION")
        col.label(text=f"[Object Mode]: spawn indices", icon="LIGHT")

        # Mesh selected is not up to date...
        mesh = obj.data
        selected_verts = [v for v in mesh.vertices if v.select]
        selected_edges = [e for e in mesh.edges if e.select]
        selected_faces = [f for f in mesh.polygons if f.select]

        # common format
        fmt = ">5.1f"
        fmt_vec = f"({{:{fmt}}}, {{:{fmt}}}, {{:{fmt}}})"


        # verts with optional world space toggle
        box = mainCol.box()
        col = box.column()
        row = col.row()
        row.alignment= "LEFT"
        row.label(text=f"verts: {len(selected_verts)}")
        row.prop(self, "edit_showWorld")
        for v in selected_verts:
            if self.edit_showWorld: pos = obj.matrix_world @ v.co
            else: pos = v.co
            col.label(text=f"{v.index}: " + f"{fmt_vec}".format(*pos))

        # optional edges
        open, box = ui.draw_toggleBox(self, "edit_showEdges", mainCol)
        if open:
            col = box.column()
            col.label(text=f"edges: {len(selected_edges)}")
            for e in selected_edges: col.label(text=f"{e.index}: {e.key}")

        # faces with option too
        box = mainCol.box()
        col = box.column()
        row = col.row()
        row.alignment= "LEFT"
        row.label(text=f"faces: {len(selected_faces)}")
        row.prop(self, "edit_showFaceCenters")
        if (self.edit_showFaceCenters):
            for f in selected_faces:
                if self.edit_showWorld: pos = obj.matrix_world @ f.center
                else: pos = f.center
                col.label(text=f"{f.index}: " + f"{fmt_vec}".format(*pos))
        else:
            for f in selected_faces: col.label(text=f"{f.index}: {f.vertices[:]}")

#-------------------------------------------------------------------
# Blender events

util_classes_pt = [
    Info_Inpect_PT,
]