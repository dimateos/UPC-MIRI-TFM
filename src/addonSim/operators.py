#import bpy
#from bpy.types import Operator

# Libraries
import math
import os
import random
import time

import bpy
import bmesh
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector


# -------------------------------------------------------------------

class MW_gen_OT_(Operator):
    bl_idname = "mw.gen"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout

    def execute(self, context):
        keywords = self.as_keywords()  # ignore=("blah",)

        return {'FINISHED'}


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
)

register, unregister = bpy.utils.register_classes_factory(classes)
