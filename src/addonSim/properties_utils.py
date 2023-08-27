import bpy
import bpy.types as types
import bpy.props as props

from .utils_dev import DEV


#-------------------------------------------------------------------

class Prop_inspector(types.PropertyGroup):
    """ Meta filters to display/edit a property group in a panel """

    meta_show_props: props.BoolProperty(
        # NOTE:: text name to be replaced in the ui
        description="Show properties",
        default=False,
    )

    meta_propFilter: props.StringProperty(
        name="Filter id", description="Separate values with commas, start with `-` for a excluding filter.",
        default="",
    )
    meta_propDefault: props.BoolProperty(
        name="default", description="Include default unchanged props",
        default=True,
    )

    meta_propEdit: props.BoolProperty(
        name="edit", description="Enable editting the props",
        default=False,
    )
    meta_propShowId: props.BoolProperty(
        name="id", description="Show property id or its name",
        default=True,
    )

    # will group foldable sections with "debug" as part of its name
    meta_show_tmpDebug: props.BoolProperty(
        name="debug...", description="Show debug properties",
        default=False,
    )