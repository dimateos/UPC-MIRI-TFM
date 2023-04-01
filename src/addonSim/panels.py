import bpy
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
    bl_options = {'DEFAULT_CLOSED'}

    #@classmethod
    #def poll(cls, context):
    #    ob = context.active_object
    #    return (ob and ob.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        col = layout.column()
        col.label(text="label")

        #col.operator('mesh.ant_displace', text="Mesh Displace", icon="RNDCURVE")
        #col.operator('mesh.ant_slope_map', icon='GROUP_VERTEX')
        #if ob.ant_landscape.keys() and not ob.ant_landscape['sphere_mesh']:
        #    col.operator('mesh.eroder', text="Landscape Eroder", icon='SMOOTHCURVE')


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