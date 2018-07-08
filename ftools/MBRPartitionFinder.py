import sys
from ftools.mbr import TableEntry
from ftools.vdrive import Drive


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
