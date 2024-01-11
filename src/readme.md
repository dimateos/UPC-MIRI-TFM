# Source folder
* ``addon/``: simple initial implementation heavily dependant on Blender fracture code
* ``addonSim/``: **FULL IMPLEMENTATION**
    * There is a lot of code around blender Operators API, scene context and its UI (panels and serializable properties)!
    * Most relevant for SIM (ordered): ``mw_sim``, ``mw_resistance``, ``mw_links``, ``mw_cont``... Invoked from ``operators``, ``operators_dm`` is used for debug/utils.
    * Tweaking default params (all have descriptions for tooltips): ``properties``. Some meta props/debug flags: ``properties_util``, ``properties_global``, ``preferences``, ``utils_dev``
* ``test/``: just some test code and notebooks

# Voro++ (python)
* My fork with required features: https://github.com/dimateos/UPC-MIRI-TFM-tess

# Development
* I used *vscode* with the following Blender development extension: https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development 
* Some required configuration is already store in the workspace settings: https://github.com/dimateos/UPC-MIRI-TFM-erosion/blob/main/.vscode/settings.json
* There are several util [``scripts/``](https://github.com/dimateos/UPC-MIRI-TFM-erosion/tree/main/scripts): e.g. when not starting off from a full portable Blender release, use ``install_deps.bat`` to install all packages (includes compiling and installing local voro++ repo)