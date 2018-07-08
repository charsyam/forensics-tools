import struct

PARTITION_ACTIVE = {
    0x80 : "ACTIVE",
    0x00 : "INACTIVE"
}

PARTITION_TYPE = {
    0x07: "NTFS",
    0x0E: "FAT16",
    0x05: "EBR(CHS)",
    0x0F: "EBR(LBA)"
}

class TableEntry(object):
    def __init__(self, data):
        self.active = data[0]
        self.chs1 = [data[1], data[2], data[3]]
        self.partition_type = data[4]
        self.chs2 = [data[5], data[6], data[7]]
        self.lba = struct.unpack_from("<I", data, 8)[0]
        self.size = struct.unpack_from("<I", data, 12)[0]

    def __repr__(self):
        msg = "Active: {}\n".format(PARTITION_ACTIVE[self.active])
        try:
            msg += "parition_type: {}\n".format(PARTITION_TYPE[self.partition_type])
        except KeyError:
            msg += "parition_type: {}\n".format(self.partition_type)
        msg += "size: {}\n".format(self.size)
        msg += "lba: {}\n".format(self.lba)
        msg += "chs1: {c}, {h}, {s}\n".format(c=self.chs1[0], h=self.chs1[1], s=self.chs1[2])
        msg += "chs2: {c}, {h}, {s}\n".format(c=self.chs2[0], h=self.chs2[1], s=self.chs2[2])
        return msg
