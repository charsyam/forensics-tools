class VFS(object):
    DEFAULT_SECTORS_PER_CLUSTER = 8
    def __init__(self, drive, spc = DEFAULT_SECTORS_PER_CLUSTER):
        self.drive = drive
        self.spc = spc

    def set_spc(self, spc):
        self.spc = spc

    def read(self, cluster, count=1):
        return self.drive.read(cluster, self.spc * count)
