class Drive(object):
    def __init__(self, drive, block_size=512):
        self.drive = open(drive, "rb")
        self.drive.seek(0)
        self.block_size = block_size

    def get_block_size(self):
        return self.block_size

    def seek(self, sector):
        self.drive.seek(sector * self.block_size)

    def read(self, sector, count=1):
        self.seek(sector)
        return self.drive.read(self.block_size * count)
