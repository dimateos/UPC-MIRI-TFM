
class UnionFind:
    """ Simple union-find to count connected components w/ path compression
        * also with dynamic enlarging of the container
        * TODO document methods
    """
    _enabled_path_compression = True

    def __init__(self, size):
        self.size = size
        # initially all elements disconnected
        self.parents = [i for i in range(size)]
        self.num_components = size

    def enlarge_dynamic(self, new_size):
        # grow the container and add new disconected components at the end
        if new_size <= self.size: return
        old_size = self.size
        self.size = new_size
        # init new components as disconnected
        self.parents += [i for i in range(old_size, new_size)]
        self.num_components += new_size-old_size

    def find_parent(self, elem):
        p = elem
        # an element is a root parent if its parent is itself
        while p != self.parents[p]:
            # backtrack until we find the root parent
            p = self.parents[p]

        # compress path taken so all elements point to root directly
        if UnionFind._enabled_path_compression:
            tmp_elem = elem
            while tmp_elem != p:
                tmp_parent = self.parents[tmp_elem]
                self.parents[tmp_elem] = p
                tmp_elem = tmp_parent

        return p

    def union(self, a, b):
        # find root parent of both elements
        p1 = self.find_parent(a)
        p2 = self.find_parent(b)
        # already connected components
        if p1 == p2: return

        # merge components by setting one parent as child
        self.parents[p2] = p1
        self.num_components -= 1

    def union_dynamic(self, a, b):
        # check if enlarge is required before union
        if a >= self.size: self.enlarge_dynamic(a+1)
        if b >= self.size: self.enlarge_dynamic(b+1)
        self.union(a, b)

    def retrieve_components(self):
        # use a dictionary of lists to separate the indices
        componets = dict()
        for i in range(self.size):
            parent = self.find_parent(i)
            try:
                componets[parent].append(i)
            except:
                componets[parent] = list()
                componets[parent].append(i)

        return list(componets.values())