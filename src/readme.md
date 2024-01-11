# Source folder
* ``addon/``: simple initial implementation heavily dependant on Blender fracture code
* ``addonSim/``: full implementation
    * 
* ``test/``: just some test code and notebooks

# Voro++ (python)
* My fork with required features: https://github.com/dimateos/UPC-MIRI-TFM-tess

# Development
* I used *vscode* with the following Blender development extension: https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development 
* Some required configuration is already store in the workspace settings: https://github.com/dimateos/UPC-MIRI-TFM-erosion/blob/main/.vscode/settings.json
* There are several util [``scripts/``](https://github.com/dimateos/UPC-MIRI-TFM-erosion/tree/main/scripts): e.g. when not starting off from a full portable Blender release, use ``install_deps.bat`` to install all packages (includes compiling and installing local voro++ repo)