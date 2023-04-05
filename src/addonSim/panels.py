import bpy
from .properties import SnowSettings
#from . import operators as ops

panel_cat = "Dev"



# -------------------------------------------------------------------

class MW_gen_Panel(bpy.types.Panel):
    bl_category = panel_cat
    bl_label = "MW_gen"
    bl_idname = "MW_PT_gen"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return (ob and ob.type == 'MESH')

    def draw(self, context):
        layout = self.layout

        # Fracture object
        ob = context.active_object
        if not ob.mw_gen:
            col = layout.column()
            col.label(text="no mw")
            col.operator('mw.gen', text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            col = layout.column()
            col.label(text="mw")
            col.operator('mw.gen', text="EDIT Fracture", icon="STICKY_UVS_VERT")

            box = layout.box()
            col = box.column()
            col.label(text="Summary")

def draw_gen_cfg(self, context):
    layout: bpy.types.UILayout = self.layout
    context: bpy.types.Context = context

    box = layout.box()
    col = box.column()
    col.label(text="Point Source")
    rowsub = col.row()
    rowsub.prop(self, "source")
    rowsub = col.row()
    rowsub.prop(self, "source_limit")
    rowsub.prop(self, "source_noise")
    #rowsub = col.row()
    #rowsub.prop(self, "cell_scale")

    box = layout.box()
    col = box.column()
    col.label(text="Margins")
    rowsub = col.row(align=True)
    rowsub.prop(self, "margin_box_bounds")
    rowsub.prop(self, "margin_face_bounds")

    box = layout.box()
    col = box.column()
    col.label(text="Summary")
    # TODO toggleable sections? + summary in sidebar

    box = layout.box()
    col = box.column()
    col.label(text="DEBUG")
    # TODO convex hull options?
    # TODO decimation too -> original faces / later


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)