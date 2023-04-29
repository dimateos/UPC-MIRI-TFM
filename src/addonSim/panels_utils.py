import bpy
import bpy.types as types
import bpy.props as props
from mathutils import Vector, Matrix

from .preferences import getPrefs, ADDON
from . import operators_utils as ops_util

from . import ui
from . import utils_geo
from .utils_dev import DEV


# OPT:: coherent poll to disable OT vs not spawning the ui
# OPT:: add deps graph calc check + also for mesh indices spawn
#-------------------------------------------------------------------

class Info_Inpect_PT(types.Panel):
    bl_idname = "DM_PT_info_inpect"
    """ PT bl_idname must have _PT_ e.g. TEST_PT_addon"""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    #bl_context = "objectmode"
    bl_category = ADDON.panel_cat

    bl_label = "DM_info"
    bl_options = {'DEFAULT_CLOSED'}
    NOTIFY_NO_SELECTED = False

    def draw(self, context):
        layout = self.layout

        # Something selected, not last active
        if not context.selected_objects:
            col = layout.column()
            if self.NOTIFY_NO_SELECTED:
                col.label(text="No object selected...", icon="ERROR")
            else:
                col.label(text="...")
            return

        if not context.active_object:
            col = layout.column()
            col.label(text="Selected but removed active?", icon="ERROR")
            return

        # draw specific mode
        self._obj = context.active_object
        if bpy.context.mode == 'OBJECT':
            self.drawMode_object(context)
        elif bpy.context.mode == 'EDIT_MESH':
            self.drawMode_edit(context)


    def drawMode_object(self, context):
        layout = self.layout
        col = layout.column()
        obj = self._obj

        # mesh inspect
        mainCol, mainBox = self.draw_inspectObject(obj, col)
        # get format precision
        fmt = self.draw_precision(mainCol)

        # draw tranforms with specific precision
        self.draw_tranforms(obj, mainCol, fmt)
        mainBox.operator(ops_util.Info_PrintMatrices_OT.bl_idname, icon="LATTICE_DATA")

        # IDEA:: print mesh dicts with input text for type
        # IDEA:: toggle decimal cap + read from print op?
        # IDEA:: add an index option and print that only + its neighbours

        # some more print info
        if obj.type == 'MESH':
            col = layout.column()
            col.operator(ops_util.Info_PrintData_OT.bl_idname, icon="HELP")
            col.operator(ops_util.Info_PrintAPI_OT.bl_idname, icon="HELP")

    def drawMode_edit(self, context):
        prefs = getPrefs()
        layout = self.layout
        #obj = bpy.context.object
        obj = self._obj

        col = layout.column()
        col.enabled = False
        col.alignment = 'LEFT'
        col.scale_y = 0.8
        col.label(text=f"[toggle Edit/Object]: update", icon="QUESTION")
        col.label(text=f"[Object Mode]: spawn indices", icon="LIGHT")

        # Inspect the mesh and format decimals
        mainCol, mainBox = self.draw_inspectObject(obj, layout)
        # get format precision
        fmt = self.draw_precision(mainCol)

        self.draw_inspectData(obj, mainCol,)

    #-------------------------------------------------------------------

    def draw_inspectObject(self, obj: types.Object, layout: types.UILayout) -> tuple[types.UILayout,types.UILayout]:
        mainBox = layout.box()
        mainCol = mainBox.column()
        mainCol.label(text="Object: " + obj.name),
        mainCol.scale_y = 0.8

        # OPT:: maybe for vertices too, not just whole objects
        box = mainCol.box()
        col = box.column()
        col.label(text="Type: " + obj.type, icon="MESH_DATA")
        if obj.type == "MESH":
            mesh: types.Mesh = obj.data
            col.label(text=f"V: {len(mesh.vertices)}   E: {len(mesh.edges)}   F: {len(mesh.polygons)}   T: {len(mesh.loop_triangles)}")

        # indices spawn
        col_rowSplit = mainBox.row().split(factor=0.8)
        col_rowSplit.operator(ops_util.Util_SpawnIndices_OT.bl_idname, icon="TRACKER")
        col_rowSplit.operator(ops_util.Util_deleteIndices_OT.bl_idname, icon="CANCEL", text="")

        mainCol = mainBox.column()
        mainCol.scale_y = 0.8
        return mainCol, mainBox

    def draw_precision(self, layout: types.UILayout):
        prefs = getPrefs()

        row = layout.row()
        row.alignment= "LEFT"
        row.prop(prefs, "dm_PT_edit_showPrecision")
        return f">5.{prefs.dm_PT_edit_showPrecision}f"

    def draw_tranforms(self, obj: types.Object, layout: types.UILayout, fmt = ">6.3f"):
        fmt_vec = f"({{:{fmt}}}, {{:{fmt}}}, {{:{fmt}}})"
        from math import degrees

        # group world
        box1 = layout.box()
        col1 = box1.column()
        col1.label(text="World transform")

        matrix: Matrix = obj.matrix_world
        pos = matrix.to_translation()
        col1.label(text=f"pos: {fmt_vec}".format(*pos))
        rot = matrix.to_euler()
        rot_deg = tuple(degrees(r) for r in rot)
        col1.label(text=f"rot:  {fmt_vec}".format(*rot_deg))
        sca = matrix.to_scale()
        col1.label(text=f"sca: {fmt_vec}".format(*sca))

        # group local
        box2 = col1.box()
        col2 = box2.column()
        col2.label(text="Local transform")

        matrix: Matrix = obj.matrix_basis
        pos = matrix.to_translation()
        col2.label(text=f"pos: {fmt_vec}".format(*pos))
        rot = matrix.to_euler()
        rot_deg = tuple(degrees(r) for r in rot)
        col2.label(text=f"rot:  {fmt_vec}".format(*rot_deg))
        sca = matrix.to_scale()
        col2.label(text=f"sca: {fmt_vec}".format(*sca))

        # group centroid
        if obj.type == "MESH":
            box3 = col1.box()
            col3 = box3.column()
            col3.label(text="Local centroid (median)")
            pos = utils_geo.centroid_mesh(obj.data, log=False)
            col3.label(text=f"pos: {fmt_vec}".format(*pos))
            col3.label(text=f"len: {pos.length}")

    def draw_inspectData(self, obj: types.Object, layout: types.UILayout, fmt = ">6.3f"):
        prefs = getPrefs()
        fmt_vec = f"({{:{fmt}}}, {{:{fmt}}}, {{:{fmt}}})"

        # Mesh selected is not up to date...
        mesh = obj.data
        selected_verts = [v for v in mesh.vertices if v.select]
        selected_edges = [e for e in mesh.edges if e.select]
        selected_faces = [f for f in mesh.polygons if f.select]

        # verts with optional world space toggle
        open, box = ui.draw_toggleBox(prefs, "dm_PT_edit_showVerts", layout)
        if open:
            col = box.column()
            row = col.row()
            row.alignment= "LEFT"
            row.label(text=f"verts: {len(selected_verts)}")
            row.prop(prefs, "dm_PT_info_edit_showWorld")
            for v in selected_verts:
                if prefs.dm_PT_info_edit_showWorld: pos = obj.matrix_world @ v.co
                else: pos = v.co
                col.label(text=f"{v.index}: " + f"{fmt_vec}".format(*pos))

        # edges
        open, box = ui.draw_toggleBox(prefs, "dm_PT_edit_showEdges", layout)
        if open:
            col = box.column()
            col.label(text=f"edges: {len(selected_edges)}")
            for e in selected_edges: col.label(text=f"{e.index}: {e.key}")

        # faces with option too
        open, box = ui.draw_toggleBox(prefs, "dm_PT_edit_showFaces", layout)
        if open:
            col = box.column()
            row = col.row()
            row.alignment= "LEFT"
            row.label(text=f"faces: {len(selected_faces)}")
            row.prop(prefs, "dm_PT_edit_showFaceCenters")
            if (prefs.dm_PT_edit_showFaceCenters):
                for f in selected_faces:
                    if prefs.dm_PT_info_edit_showWorld: pos = obj.matrix_world @ f.center
                    else: pos = f.center
                    col.label(text=f"{f.index}: " + f"{fmt_vec}".format(*pos))
            else:
                for f in selected_faces: col.label(text=f"{f.index}: {f.vertices[:]}")

#-------------------------------------------------------------------
# Blender events

util_classes_pt = [
    Info_Inpect_PT,
]