> :star: Probably the simplest setup would be picking the portable Blender version with the addon already install, available in the [releases page](https://github.com/dimateos/UPC-MIRI-TFM-erosion/releases). Then you can edit local the python scripts to test simple tweaks.

# Scripts folder (for windows)
* ``env.bat`` sets all non-portable paths, so you may have to edit it
* ``install_deps.bat`` can be used to install all packages, useful when not starting off from a full portable Blender release. This includes compiling and installing local voro++ repo, whose path must be set in ``env.bat``
* ``install_voro.bat`` can be used to install voro++ from the remote git repository without having to fork it manually etc
* ``_test.bat`` contains some tests commands to see pip install options and check remote install

<details><summary>Pip freeze of local env (deployed with Blender portable build)</summary>

```sh
# bpip_backup.bat
asttokens==2.2.1
attrs==22.2.0
autopep8==1.6.0
backcall==0.2.0
certifi==2021.10.8
charset-normalizer==2.0.10
click==8.1.3
colorama==0.4.6
comm==0.1.3
contourpy==1.1.0
cycler==0.11.0
Cython==0.29.26
debugpy==1.6.6
decorator==5.1.1
dill==0.3.6
exceptiongroup==1.1.0
executing==1.2.0
fake-bpy-module-3.4==20230117
Flask==2.2.2
fonttools==4.42.0
idna==3.3
imgui==1.4.1
iniconfig==2.0.0
ipykernel==6.22.0
ipython==8.12.0
itsdangerous==2.1.2
jedi==0.18.2
Jinja2==3.1.2
jupyter_client==8.1.0
jupyter_core==5.3.0
kiwisolver==1.4.4
markdown-it-py==2.1.0
MarkupSafe==2.1.2
matplotlib==3.7.2
matplotlib-inline==0.1.6
mdurl==0.1.2
nest-asyncio==1.5.6
networkx==3.1
numpy==1.22.0
packaging==23.0
pandas==2.0.3
parso==0.8.3
pickleshare==0.7.5
Pillow==10.0.0
platformdirs==3.2.0
pluggy==1.0.0
prompt-toolkit==3.0.38
psutil==5.9.4
pure-eval==0.2.2
py==1.11.0
pycodestyle==2.8.0
Pygments==2.14.0
pyparsing==3.0.9
pytest==7.2.2
python-dateutil==2.8.2
pytz==2023.3
pywin32==306
pyzmq==25.0.2
requests==2.27.1
rich==13.3.1
setuptools-scm==7.1.0
six==1.16.0
stack-data==0.6.2
taichi==1.4.1
-e git+https://github.com/dimateos/UPC-MIRI-TFM-tess@09ea5d6cd87b36558d1cc9ba1017578d83ab61e7#egg=tess
toml==0.10.2
tomli==2.0.1
tornado==6.2
traitlets==5.9.0
typing_extensions==4.5.0
tzdata==2023.3
urllib3==1.26.8
wcwidth==0.2.6
Werkzeug==2.2.2
zstandard==0.16.0
```
</details>

> :email: Feel free to contact me through email...