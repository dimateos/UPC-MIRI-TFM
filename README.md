# UPC-MIRI-TFM

* **DIEGO MATEOS ARLANZÓN** diego.mateos@estudiantat.upc.edu

Thesis supervisors:
* OSCAR ARGUDO MEDRANO
* ANTONIO SUSIN SANCHEZ


| Oral defence     | Thursday, October 19, 2023                                |
|------------------|-----------------------------------------------------------|
| Degree           | Master's Degree in Innovation and Research in Informatics |
| Specialization   | Computer Graphics and Virtual Reality                     |
| Spoken language  | English                                                   |
| Written language | English                                                   |
| Qualification    | 10                                                        |

> :star: Full **report** and **presentation** PDFs available in the [releases page](https://github.com/dimateos/UPC-MIRI-TFM-erosion/releases), along with a portable Blender version with the addon ready to test.

# Simulation of mechanical weathering for modeling rocky terrains

Synthetic terrains play a vital role in various applications, including entertainment, training, and simulation. While significant progress has been made in terrain generation, existing methods often focus on large-scale features, relying on 2D elevation maps to model them. However, rocky terrains like those found in alpine environments have many detail features like sharp ridges, loose blocks or overhangs that are poorly represented in this maps, so it is common to model them using textures. 

Instead, in this project, we aim to generate plausible rocky geometry on top of existing 3D models. We propose a method based on a simplified simulation of mechanical erosion processes commonly found in high altitude terrains such as percolation and freeze-thaw weathering. The process can be controlled through a series of intuitive parameters and its iterative nature lets an artist apply it multiple times until sufficient erosion is achieved.

Additionally, we developed an artist-friendly tool integrated as add-on into Blender, which is a widely used 3D modeling software. This rich integration streamlines their workflow, eliminating the need for external applications and facilitating direct interaction with the model geometry before and after the simulated erosion.

## Keywords
* *Computer Graphics, 3D Modelling, Computer Simulation, Rocky Terrains, Mechanical Weathering.*

## References
* Not yet available in [UPCommons](https://upcommons.upc.edu/handle/2099.1/20414) library (*seems like they upload them only in June*)
* Complete bibliography accessible in [``references.bib``](https://github.com/dimateos/UPC-MIRI-TFM-erosion/blob/main/report/references.bib) (*the report section contains only cited ones*)
* Full **report** and **presentation** PDFs available in the [releases page](https://github.com/dimateos/UPC-MIRI-TFM-erosion/releases), along with a portable Blender version with the addon ready to test.
* Sources and development information available in [src/](https://github.com/dimateos/UPC-MIRI-TFM-erosion/tree/main/src)
* Voro++ (python): My fork with updated features can be found [here](https://github.com/dimateos/UPC-MIRI-TFM-tess)

> :email: Feel free to contact me through email...

## Known issues / Future work
* **Method**: The simulation does not include stability computations to remove excessively overhanging blocks.
* **Implementation**: The addon is quite stable but not all scene serialization was implemented: state might break with UNDO/REDO on some operations, it is also not stored statically in the .blend file.

> :mag: More details in the report...

# Pictures

### Background
We propose a physically inspired method based on the freeze-thaw cycle, which is the main erosion process that takes place in mountainous landscapes.
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/2_back/erosion-ft.png">

### Method
After a fracture structure is generated, we simulate the following erosion process: water infiltration, propagation, absorption, link erosion and cell detachment computation.
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/4_method/sim-exit.png">
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/4_method/sim-exit-large.png">
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/4_method/sim-split-core.png">

### Implementation
We developed a rich Blender add-on that includes tons of utils to ease development.
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/5_blender/bl-overview.png">
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/5_blender/bl-sim.png">
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/5_blender/utils.png">

### Results
Samples of 3D results after a large amount of infiltrations.
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/6_results/sim-chunk-anim.png">
<img style="display: block; float: none; margin-left: auto; margin-right: auto; margin-top: 15px; margin-bottom: 15px; width:80%;" src="report/img/6_results/sim-hill-20000.png">


