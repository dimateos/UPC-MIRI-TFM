import bpy
import bpy.types as types
import bpy.props as props
from mathutils import Vector, Matrix

from .preferences import getPrefs, ADDON
from . import operators_utils as ops_util

from . import ui
from . import utils
from . import utils_geo
from .utils_dev import DEV


# OPT:: coherent poll to disable OT vs not spawning the ui
# OPT:: add deps graph calc check + also for mesh indices spawn
#-------------------------------------------------------------------

class Info_inpect_PT(types.Panel):
    bl_idname = "DM_PT_info_inpect"
    """ PT bl_idname must have _PT_ e.g. TEST_PT_addon"""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    #bl_context = "objectmode"
    bl_category = ADDON.panel_cat

    bl_label = "DM_info"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = getPrefs()
        layout = self.layout

        # inspect panel
        open, box = ui.draw_toggleBox(prefs, "dm_PT_meta_show_info", layout)
        if open:
            # Something selected + check last active
            if not context.selected_objects:
                col = box.column()
                col.label(text="No object selected...", icon="ERROR")
            elif not context.active_object:
                col = box.column()
                col.label(text="Selected but removed active?", icon="ERROR")

            else:
                obj = context.selected_objects[-1]

                # draw common inspect
                mainCol, mainBox = self.draw_inspectObject(obj, box)

                # draw specific mode detailed info
                open, box = ui.draw_toggleBox(prefs, "dm_PT_meta_show_full", mainCol)
                if open:
                    if bpy.context.mode == 'OBJECT':        self.drawMode_object(context, obj, box)
                    elif bpy.context.mode == 'EDIT_MESH':   self.drawMode_edit(context, obj, box)

        # debug options
        open, box = ui.draw_toggleBox(prefs, "dm_PT_meta_show_tmpDebug", layout)
        if open:
            # fix orphan meshes
            col_rowSplit = box.row().split(factor=0.8)
            col_rowSplit.label(text=f"Scene DATA - orphans", icon="SCENE_DATA")
            col_rowSplit.operator(ops_util.Util_deleteOrphanData_OT.bl_idname, icon="UNLINKED", text="")

            box.prop(prefs, "dm_PT_orphans_collection")
            col = box.column()

            # dynamically check it has the collection
            for colName in prefs.dm_PT_orphans_collection.split(","):
                colName = colName.strip()
                if not hasattr(bpy.data, colName): continue
                collection = getattr(bpy.data, colName)
                col.label(text=f"{colName}: {len(collection)}", icon="LIBRARY_DATA_OVERRIDE_NONEDITABLE")

        layout.operator(ops_util.Debug_testCode_OT.bl_idname, icon="MATSHADERBALL")

    def drawMode_object(self, context, obj, box):
        # draw tranforms with specific precision
        fmt = self.draw_precision(box)
        self.draw_tranforms(obj, box, fmt)
        box.operator(ops_util.Info_printMatrices_OT.bl_idname, icon="LATTICE_DATA")

        # IDEA:: print mesh dicts with input text for type
        # IDEA:: toggle decimal cap + read from print op?
        # IDEA:: add an index option and print that only + its neighbours

        # some more print info
        if obj.type == 'MESH':
            col = box.column()
            col.operator(ops_util.Info_printData_OT.bl_idname, icon="SPREADSHEET")
            col.operator(ops_util.Info_printQueries_OT.bl_idname, icon="SPREADSHEET")
            col.operator(ops_util.Info_printAPI_OT.bl_idname, icon="HELP")

    def drawMode_edit(self, context, obj, box):
        prefs = getPrefs()

        # Use selected data or input it
        col_rowSplit = box.row().split(factor=0.5)
        col_rowSplit.scale_y = 1.2
        col_rowSplit.prop(prefs, "dm_PT_edit_useSelected")
        col_rowSplit.prop(prefs, "dm_PT_edit_showLimit")
        col = box.column()

        # tip about not updated
        if prefs.dm_PT_edit_useSelected:
            col.enabled = False
            col.alignment = 'LEFT'
            #col.scale_y = 0.8
            col.label(text=f"[toggle Edit/Object] for updates", icon="QUESTION")
            #col.label(text=f"[Object Mode]: spawn indices", icon="LIGHT")
        # filter for manual selection
        else:
            col.prop(prefs, "dm_PT_edit_indexFilter")

        # get format precision
        fmt = self.draw_precision(box)

        self.draw_inspectData(obj, box, fmt)

    #-------------------------------------------------------------------

    def draw_inspectObject(self, obj: types.Object, layout: types.UILayout) -> tuple[types.UILayout,types.UILayout]:
        mainBox = layout

        # indices spawn
        col_rowSplit = mainBox.row().split(factor=0.8)
        col_rowSplit.operator(ops_util.Util_spawnIndices_OT.bl_idname, icon="TRACKER")
        col_rowSplit.operator(ops_util.Util_deleteIndices_OT.bl_idname, icon="CANCEL", text="")

        col = mainBox.column()
        col.scale_y = 0.8

        # obj name
        box = col.box()
        col_rowSplit = box.row().split(factor=0.7)
        col_rowSplit.label(text=f"{obj.name}", icon="OBJECT_DATAMODE")
        col_rowSplit.label(text=f"(name)")

        # obj mesh
        col = box.column()
        col_rowSplit = col.row().split(factor=0.7)
        col_rowSplit.label(text=f"{obj.type}", icon="MESH_DATA")
        col_rowSplit.label(text=f"(type)")

        if obj.type == "MESH":
            mesh: types.Mesh = obj.data
            col.label(text=f" V: {len(mesh.vertices)}   E: {len(mesh.edges)}   F: {len(mesh.polygons)}   T: {len(mesh.loop_triangles)}") # icon="DOT"

        mainCol = mainBox.column()
        mainCol.scale_y = 0.8
        return mainCol, mainBox

    def draw_precision(self, layout: types.UILayout):
        prefs = getPrefs()

        row = layout.row().split(factor=0.45)
        row.alignment= "LEFT"
        row.scale_y = 0.9
        row.label(text=f"Precision", icon="TRACKING_FORWARDS_SINGLE")
        row.prop(prefs, "dm_PT_info_showPrecision")
        return f">5.{prefs.dm_PT_info_showPrecision}f"

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
        limit = prefs.dm_PT_edit_showLimit
        mesh = obj.data

        # verts with optional world space toggle
        open, box = ui.draw_toggleBox(prefs, "dm_PT_edit_showVerts", layout)
        if open:
            if prefs.dm_PT_edit_useSelected: selected_verts = [v for v in mesh.vertices if v.select]
            else: selected_verts = utils.get_filtered(mesh.vertices, prefs.dm_PT_edit_indexFilter)

            col = box.column()
            row = col.row()
            row.alignment= "LEFT"
            row.label(text=f"verts: {len(selected_verts)}")
            row.prop(prefs, "dm_PT_info_edit_showWorld")
            for v in selected_verts[:limit]:
                if prefs.dm_PT_info_edit_showWorld: pos = obj.matrix_world @ v.co
                else: pos = v.co
                col.label(text=f"{v.index}: " + f"{fmt_vec}".format(*pos))
            if len(selected_verts) > limit: col.label(text=f"...")

        # edges
        open, box = ui.draw_toggleBox(prefs, "dm_PT_edit_showEdges", layout)
        if open:
            if prefs.dm_PT_edit_useSelected: selected_edges = [e for e in mesh.edges if e.select]
            else: selected_edges = utils.get_filtered(mesh.edges, prefs.dm_PT_edit_indexFilter)

            col = box.column()
            col.label(text=f"edges: {len(selected_edges)}")
            for e in selected_edges[:limit]: col.label(text=f"{e.index}: {e.key}")
            if len(selected_edges) > limit: col.label(text=f"...")

        # faces with option too
        open, box = ui.draw_toggleBox(prefs, "dm_PT_edit_showFaces", layout)
        if open:
            if prefs.dm_PT_edit_useSelected: selected_faces = [f for f in mesh.polygons if f.select]
            else: selected_faces = utils.get_filtered(mesh.polygons, prefs.dm_PT_edit_indexFilter)

            col = box.column()
            row = col.row()
            row.alignment= "LEFT"
            row.label(text=f"faces: {len(selected_faces)}")
            row.prop(prefs, "dm_PT_edit_showFaceCenters")
            if (prefs.dm_PT_edit_showFaceCenters):
                for f in selected_faces[:limit]:
                    if prefs.dm_PT_info_edit_showWorld: pos = obj.matrix_world @ f.center
                    else: pos = f.center
                    col.label(text=f"{f.index}: " + f"{fmt_vec}".format(*pos))
            else:
                for f in selected_faces[:limit]: col.label(text=f"{f.index}: {f.vertices[:]}")
            if len(selected_faces) > limit: col.label(text=f"...")

#-------------------------------------------------------------------
# Blender events

util_classes_pt = [
    Info_inpect_PT,
]