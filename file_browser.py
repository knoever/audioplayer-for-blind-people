import os

class Meta:
    def __init__(self, path, parent):
        """
        :type path: str
        :type parent: Folder
        """
        self.parent = parent
        self.path = path

    def meta_file(self, key):
        assert self.parent
        a, b = os.path.split(self.path)
        meta = os.path.join(a, '.meta')
        if not os.path.exists(meta):
            os.makedirs(meta)
        return os.path.join(meta, b + '_' + key)

    def __str__(self):
        return os.path.split(self.path)[1]

class Folder:
    def __init__(self, path):
        
        self._entries = []
        for e in os.listdir(path):
            if e == '.meta':
                continue
            e = os.path.join(path, e)
            if os.path.isdir(e):
                self._entries.append(Folder(e, self))
            elif os.path.isfile(e):
                self._entries.append(File(e, self))
            else:
                raise Exception('Neither a file nor a directory: %s' % e)
        self._entries.sort(key=lambda x: x.path)
    
    def __str__(self):
        for e in self._entries:
            print(str(e))

    def is_folder(self):
        return True

    def is_empty(self):
        return len(self._entries) == 0

    def entries(self, recursive=False):
        ret = list(self._entries)
        #if recursive:
         #   for e in self._entries:
          #      if e.is_folder():
           #         ret.extend(e.entries(recursive=True))
        return ret

    def next_entry(self, entry):
        entries = self.entries()
        next = entries.index(entry) + 1
        if next == len(entries):
            return None
        return entries[next]

class File(Meta):
    def __init__(self, path, parent):
        super(File, self).__init__(path, parent)

    def is_folder(self):
        return False

PATH = '/Users/bellcha/OneDrive'  
assert PATH[-1] != '/'

#root = Folder(PATH, None)

for e in os.listdir(PATH):
    f = os.path.join(PATH,e)

    if os.path.isfile(f):
        print(File(f,None))
    else:
        print('No')