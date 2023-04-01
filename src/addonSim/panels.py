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

    #@classmethod
    #def poll(cls, context):
    #    ob = context.active_object
    #    return (ob and ob.type == 'MESH')

    def draw(self, context):
        #layout = self.layout
        #ob = context.active_object
        #col = layout.column()
        #col.label(text="label")

        #col.operator('mesh.ant_displace', text="Mesh Displace", icon="RNDCURVE")
        #col.operator('mesh.ant_slope_map', icon='GROUP_VERTEX')
        #if ob.ant_landscape.keys() and not ob.ant_landscape['sphere_mesh']:
        #    col.operator('mesh.eroder', text="Landscape Eroder", icon='SMOOTHCURVE')
        #        col.operator('mesh.eroder', text="Landscape Eroder", icon='SMOOTHCURVE')
        #            col.operator('mesh.eroder', text="Landscape Eroder", icon='SMOOTHCURVE')

        scn = context.scene
        settings: SnowSettings = scn.snow
        layout = self.layout

        col = layout.column(align=True)
        col.prop(settings, 'coverage', slider=True)
        col.prop(settings, 'height')

        layout.use_property_split = True
        layout.use_property_decorate = False
        flow = layout.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=True)
        col = flow.column()
        col.prop(settings, 'vertices')

        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("snow.create", text="Add Snow", icon="FREEZE")

        row = layout.row(align=True)
        row.label(text=str(settings.testRaw_int))
        row.label(text=settings.testRaw_dict["yes"])

        row = layout.row(align=True)
        row.label(text=str(settings.testRaw_class.id))


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