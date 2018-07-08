import struct
import sys
from vdrive import Drive

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


class MBRPartitionFinder(object):
    def __init__(self, drive):
        self.drive = drive

    def is_ebr(self, ptype):
        return ptype in [0x05, 0x0F]

    def _parse_partitions(self, ebr_offset, offset):
        partitions = []
        sector = self.drive.read(offset)
        tables = self.get_table_entries(sector)

        for table in tables:
            if self.is_ebr(table.partition_type):
                new_offset = ebr_offset + table.lba
                if ebr_offset == 0:
                    ebr_offset = table.lba

                parts = self._parse_partitions(ebr_offset, new_offset)

                for part in parts:
                    partitions.append(part)
            else:
                table.lba += offset
                partitions.append(table)

        return partitions

    def parse(self):
        return self._parse_partitions(0, 0)

    def get_table_entries(self, sector):
        partitions = []
        start = 446
        for _ in range(4):
            end = start + 16
            table = TableEntry(sector[start:end])
            if table.size > 0:
                partitions.append(table)

            start += 16

        return partitions


if __name__ == '__main__':
    # Windows : "\\\\.\\PhysicalDrive%d"
    # Linux : "/dev/sda"

    drive = Drive(sys.argv[1])
    finder = MBRPartitionFinder(drive)
    partitions = finder.parse()
    for partition in partitions:
        print(partition)
        vbr = drive.read(partition.lba)
        print(vbr)
        print("=================")
        print("=================")
