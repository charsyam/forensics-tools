class BlockFile(object):
    def __init__(self, vfs, filesize, extends):
        self.vfs = vfs
        self.filesize = filesize
        self.extends = extends

    def read(self, offset, size):
        blocks = self.bget(offset, size)
        buf = b""

        for block in blocks:
            buf += self.vfs.read(block[0], block[1])

        return buf

    def bget(self, offset, size):
        blocks = []
        current_bound = 0
        nsize = size
        noffset = offset

        store = False
        added = 0

        for extend in self.extends:
            nblocks = extend[1]
            start_offset = extend[0]

            current_bound += nblocks

            if not store and offset < current_bound:
                store = True
                capa = current_bound - offset
                added = capa if nsize > capa else nsize
                blocks.append((start_offset+noffset, added))
                nsize -= added

            elif store == False:
                noffset -= extend[1]

            elif store:
                added = nblocks if nblocks < nsize else nsize
                blocks.append((start_offset, added))
                nsize -= added

            if nsize <= 0:
                break
                
        return blocks
