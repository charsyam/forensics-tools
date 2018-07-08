class Drive(object):
    def __init__(self, drive, sector_size=512):
        self.drive = open(drive, "rb")
        self.drive.seek(0)
        self.sector_size = sector_size

    def seek(self, sector):
        self.drive.seek(sector * self.sector_size)

    def read(self, sector, count=1):
        self.seek(sector)
        return self.drive.read(self.sector_size * count)
