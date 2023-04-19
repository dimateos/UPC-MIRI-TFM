# Avoiding circular imports around properties and preferences management
# -------------------------------------------------------------------

def getProps_names(src):
    """ Get all properties names of an object, e.g. not just the modified ones in PropertyGroup.keys() """
    props_names = []

    # Avoid doc attrs and read-only RNA types, no need to trim or lowercase etc
    # To filter further props do it outside the method on the returned names
    _getProps_filter = [ "bl_", "rna_", "__" ]

    for prop_name in dir(src):
        filterMask = [ prop_name.startswith(f) for f in _getProps_filter]
        if any(filterMask): continue

        # skip callable methods
        if callable(getattr(src, prop_name)):
            continue

        props_names.append(prop_name)
    return props_names

def copyProps(src, dest):
    """ Copy all properties of the property group to the object, so not just the modified ones in src.keys() """
    # The whole property is read-only but its values can be modified, avoid writing it one by one...
    # TODO: add filter props
    props_names = getProps_names(src)
    for prop_name in props_names:
        setattr(dest, prop_name, getattr(src, prop_name))
