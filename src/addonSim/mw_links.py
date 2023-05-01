import bpy.types as types
from mathutils import Vector, Matrix

from tess import Container, Cell

from . import utils
from . import utils_geo
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

# OPT:: could use a class or an array of props? pyhton already slow so ok class?
class Link():
    keyType = tuple[int, int]

    def __init__(self, key_cells: tuple[int, int], key_faces: tuple[int, int], pos_world:Vector, dir_world:Vector, toWall=False):
        self.life = 1.0

        # no directionality
        self.key_cells: Link.keyType = key_cells
        self.key_faces: Link.keyType = key_faces

        # properties in world space
        self.pos = pos_world
        self.dir = dir_world

        # WIP:: arg? position of the key being first?
        self.toWall = toWall

        # neighs populated afterwards
        self.neighs: list[Link.keyType] = list()


#-------------------------------------------------------------------

class Links():

    def __init__(self, cont: Container, obj_shards: types.Object):
        stats = getStats()
        self.cont = cont
        self.obj_shards = obj_shards

        # TODO:: unionfind joined components + manually delete links
        # IDEA:: dynamic lists of broken?
        self.link_map: dict[Link.keyType, Link] = dict()
        self.num_toCells = 0
        self.num_toWalls = 0
        #return


        # XXX:: decouple scene from sim? calculate the FtoF map inside voro isntead of blender mesh...
        self.shard_objs: types.Object = [ shard for shard in obj_shards.children ]
        self.shard_meshes: types.Mesh= [ shard.data for shard in self.shard_objs ]
        # TODO:: the children objects are ordered lexicographically 0 1 10 11 12 13... dynamically add zeroes or sort after?

        meshes_dicts = [ utils_geo.get_meshDicts(me) for me in self.shard_meshes ]
        stats.logDt("calculated shards mesh dicts")

        # XXX:: could be calculated in voro++, also avoid checking twice...
        # XXX:: using lists or maps to support non linear cell.id?
        cont_neighs = [ cell.neighbors() for cell in cont if cell is not None ] # None cell will probably lead to asymmetry tho
        stats.logDt("calculated voro cell neighs")

        cont_neighs_faces = []
        try:
            for i,neighs in enumerate(cont_neighs):
                #faces = [ n if n<0 else cont_neighs[n].index(i) for n in neighs ]
                faces = [None] *len(neighs)
                for f,n in enumerate(neighs):
                    faces[f] = n if n<0 else cont_neighs[n].index(i)
                cont_neighs_faces.append(faces)
        except:
            # TODO:: the map could be asymetric! and .index(i) fail -> needs to be handle and maybe breaks later parts...
            DEV.log_msg(f"NO LINKS: asymetric cell neighs due to cell failed computation or tolerante issues", {"CALC", "LINKS", "ERROR"})
            print({"i":i, "faces":faces, "f":f, "neighs":neighs, "n":n, "cont_neighs[n]":cont_neighs[n] })
            return
        stats.logDt("calculated cell neighs faces")


        # IDEA:: keys to global map or direclty the links?
        # init cell dict with lists of its faces size (later index by face)
        self.keys_perCell: dict[int, list[Link.keyType]] = {cell.id: list([Link.keyType()]* len(cont_neighs[cell.id])) for cell in cont } # if cell is not None
        # init wall dict with just empty lists (some will remain empty)
        self.keys_perWall: dict[int, list[Link.keyType]] = {id: list() for id in cont.get_conainerId_limitWalls()+cont.walls_cont_idx}


        # FIRST loop to build the global dictionaries
        for cell in cont:
            #if cell is None: continue
            idx_cell = cell.id
            obj = self.shard_objs[idx_cell]
            me = self.shard_meshes[idx_cell]
            m_toWorld, mn_toWorld = utils.get_worldMatrix_normalMatrix(obj, update=True)

            for idx_face, idx_neighCell in enumerate(cont_neighs[idx_cell]):
                # get world props
                face = me.polygons[idx_face]
                pos = m_toWorld @ face.center
                normal = mn_toWorld @ face.normal

                # link to a wall, wont be repeated
                if idx_neighCell < 0:
                    key = (idx_neighCell, idx_cell)
                    key_faces = (idx_neighCell, idx_face)
                    l = Link(key, key_faces, pos, normal, toWall=True)

                    # add to mappings per wall and cell
                    self.num_toWalls += 1
                    self.link_map[key] = l
                    self.keys_perWall[idx_neighCell].append(key)
                    self.keys_perCell[idx_cell][idx_face] = key
                    continue

                # check unique links between cells
                # NOTE:: key does not include faces, expected only one face conected between cells
                key,swap = Links.getKey_swap(idx_cell, idx_neighCell)
                key_rep = key in self.link_map
                if key_rep:
                    continue

                # build the link
                idx_neighFace = cont_neighs_faces[idx_cell][idx_face]
                key_faces = Links.getKey(idx_face, idx_neighFace, swap)
                l = Link(key, key_faces, pos, normal)

                # add to mappings for both per cells
                self.num_toCells += 1
                self.link_map[key] = l
                self.keys_perCell[idx_cell][idx_face] = key
                self.keys_perCell[idx_neighCell][idx_neighFace] = key

        stats.logDt("created link map")
        #return
        # XXX:: found empty key? ()

        # SECOND loop to aggregate the links neighbours, only need to iterate keys_perCell
        for idx_cell,keys_perFace in self.keys_perCell.items():
            for idx_face,key in enumerate(keys_perFace):
                l = self.link_map[key]
                #DEV.log_msg(f"l {l.key_cells} {l.key_cells}")

                # avoid recalculating link neighs (and duplicating them)
                if l.neighs:
                    continue

                # walls only add local faces from the same cell
                if l.toWall:
                    w_neighs = meshes_dicts[idx_cell]["FtoF"][idx_face]
                    w_neighs = [ keys_perFace[f] for f in w_neighs ]
                    l.neighs += w_neighs
                    continue

                # extract idx and geometry faces neighs
                c1, c2 = l.key_cells
                f1, f2 = l.key_faces
                m1_neighs = meshes_dicts[c1]["FtoF"]
                m2_neighs = meshes_dicts[c2]["FtoF"]
                f1_neighs = m1_neighs[f1]
                f2_neighs = m2_neighs[f2]

                # the key is sorted, so query the keys per cell per each one
                c1_keys = self.keys_perCell[c1]
                c2_keys = self.keys_perCell[c2]
                c1_neighs = [ c1_keys[f] for f in f1_neighs ]
                c2_neighs = [ c2_keys[f] for f in f2_neighs ]
                l.neighs += c1_neighs + c2_neighs

        stats.logDt("aggregated link neighbours")
        logType = {"CALC", "LINKS"}
        if not self.link_map: logType |= {"ERROR"}
        DEV.log_msg(f"Found {self.num_toCells} links to cells + {self.num_toWalls} links to walls (total {len(self.link_map)})", logType)


    def getMesh(self, idx: list[int]|int) -> list[types.Mesh]|types.Mesh:
        """ return a mesh or list of meshes given idx  """
        try:
            return self.shard_meshes[idx]
        except TypeError:
            return [ self.shard_meshes[i] for i in idx ]

    def getFace(self, midx: list[int]|int, fidx: list[int]|int) -> list[types.MeshPolygon]|types.MeshPolygon:
        """ return a face or list of faces given idx  """
        try:
            return self.shard_meshes[midx].polygons[fidx]
        except TypeError:
            return [ self.shard_meshes[i].polygons[j] for i,j in zip(midx,fidx) ]


    #-------------------------------------------------------------------

    @staticmethod
    def getKey_swap(k1,k2) -> tuple[Link.keyType,bool]:
        swap = k1 > k2
        key = (k1, k2) if not swap else (k2, k1)
        return key,swap

    @staticmethod
    def getKey(k1,k2, swap) -> Link.keyType:
        key = (k1, k2) if not swap else (k2, k1)
        return key

    #-------------------------------------------------------------------

# OPT:: store links between objects -> add json parser to store persistently? or retrieve from recalculated cont?
# OPT:: register some calback on object rename? free the map or remap
# XXX:: this storage is lost on module reload tho
class Links_storage:
    bl_links: dict[str, Links] = dict()

    @staticmethod
    def addLinks(links, uniqueName):
        if uniqueName in Links_storage.bl_links:
            DEV.log_msg(f"Replacing: {uniqueName}...", {"STORAGE", "LINKS"})
        Links_storage.bl_links[uniqueName] = links

    @staticmethod
    def getLinks(uniqueName):
        try:
            return Links_storage.bl_links[uniqueName]
        except KeyError:
            DEV.log_msg(f"Get: no {uniqueName}... probably reloaded the module?", {"STORAGE", "LINKS", "ERROR"})

    @staticmethod
    def freeLinks(uniqueName):
        try:
            links = Links_storage.bl_links.pop(uniqueName)
            del links
        except KeyError:
            DEV.log_msg(f"Del: no {uniqueName}... probably reloaded the module?", {"STORAGE", "LINKS", "ERROR"})