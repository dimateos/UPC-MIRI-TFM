import bpy
import bpy.types as types
import bpy.props as props

#from .mw_links import Links, Link
from tess import Container, Cell


#-------------------------------------------------------------------

class MW_gen_cfg(types.PropertyGroup):
    #nbl_links: Links = None
    nbl_cont: Container = None

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

    #-------------------------------------------------------------------

    class sourceOptions:
        all=[
            ('VERT_OWN', "Own Verts", "Use own vertices (also set by default when other options are disabled)"),
            ('VERT_CHILD', "Child Verts", "Use child object vertices"),
            ('PARTICLE_OWN', "Own Particles", "All particle systems of the source object"),
            ('PARTICLE_CHILD', "Child Particles", "All particle systems of the child objects"),
            ('PENCIL', "Pencil", "Annotation Grease Pencil (only touching/inside the volume)"),
        ]
        enabled = {
            'VERT_OWN': True,
            'VERT_CHILD': True,
            'PARTICLE_OWN': True,
            'PARTICLE_CHILD': True,
            #'PENCIL': False,
        }
        all_keys = [ k for k in enabled.keys() ]
        default_key = 'PARTICLE_CHILD'
        fallback_key = 'VERT_OWN'
        error_key = 'NONE'
        error_option = [ (error_key, "No point found...", f"Options: {all_keys}") ]

    def source_dynamic(self, context):
        items = [
            t for t in self.sourceOptions.all
                if self.sourceOptions.enabled.get(t[0], False)
        ]
        if items: return items
        else: return self.sourceOptions.error_option.copy()

    source: props.EnumProperty(
        name="Source", description="Available source from where to retrieve points",
        items=source_dynamic, # default with numberID doesnt seem to work
        #items=sourceOptions.all, default={'VERT_OWN'},
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

    struct_namePrefix: props.StringProperty(
        name="Prefix",
        default="MW",
    )
    struct_nameOriginal: props.StringProperty()
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
    struct_showLinks_toWalls: props.BoolProperty(
        name="WIP: Links to walls", description="Voronoi cells links per face to walls",
        default=True,
    )
    struct_showLinks_perCell: props.BoolProperty(
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

    links_width: props.FloatProperty(
        name="Link width", description="WIP: how wide the base link is",
        default=0.02, min=0.005, max=0.1, step=0.05, precision=4
    )
    links_res: props.IntProperty(
        name="Link res", description="WIP: ",
        default=0, min=0, max=8,
    )

#-------------------------------------------------------------------

class MW_sim_cfg(types.PropertyGroup):
    pass

class MW_vis_cfg(types.PropertyGroup):
    pass


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_cfg,
    #MW_sim_cfg,
    #MW_vis_cfg,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.mw_gen = props.PointerProperty(
        type=MW_gen_cfg,
        name="MW_Generation", description="MW generation properties")

    #bpy.types.Object.mw_sim = props.PointerProperty(
    #    type=MW_sim_cfg,
    #    name="MW_Simulation", description="MW simulation properties")

    ## WIP maybe visualization stored in scene?
    #bpy.types.Object.mw_vis = props.PointerProperty(
    #    type=MW_vis_cfg,
    #    name="MW_Visualization", description="MW visualization properties")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

