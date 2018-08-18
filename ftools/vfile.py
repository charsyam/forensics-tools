class BlockFile(object):
    def __init__(self, vfs, filesize, extends):
        self.vfs = vfs
        self.block_size = vfs.get_block_size()
        self.extends = extends
        self.filesize = self._calculate_filesize(filesize)

    def _calculate_filesize(self, filesize):
        if filesize >= 0:
            return filesize

        bsize = self.vfs.get_block_size()
        size = 0
        for extend in self.extends:
            size += bsize * extend[1]

        return size
        
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


class VFile(BlockFile):
    def __init__(self, vfs, filesize, extends):
        super(BlockFile, self).__init__(vfs, filesize, extends)

    def read(self, offset, size):
        blocks = self.bget(offset, size)
        buf = b""

        for block in blocks:
            buf += self.vfs.read(block[0], block[1])

        return buf
