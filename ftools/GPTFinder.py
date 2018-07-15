import sys
import struct
import uuid
from vdrive import Drive


class GPTFinder(object):
    UNUSED_GUID = uuid.UUID('00000000-0000-0000-0000-000000000000')

    def __init__(self, drive):
        self.drive = drive

    def parse_header(self, data):
        signature = data[0:8]
        revision = struct.unpack_from("<I", data, 8)[0]
        header_size = struct.unpack_from("<I", data, 12)[0]
        crc32 = struct.unpack_from("<I", data, 16)[0]
        gpt_lba = struct.unpack_from("<Q", data, 24)[0]
        backup_gpt_lba = struct.unpack_from("<Q", data, 32)[0]
        first_usable_lba = struct.unpack_from("<Q", data, 40)[0]
        last_usable_lba = struct.unpack_from("<Q", data, 48)[0]
        disk_guid = uuid.UUID(bytes=data[56:72])
        partition_etnry_start_lba = struct.unpack_from("<Q", data, 72)[0]
        number_of_partition_entries = struct.unpack_from("<I", data, 80)[0]
        size_of_partition_entry = struct.unpack_from("<I", data, 84)[0]
        crc32_of_partition_array = struct.unpack_from("<I", data, 88)[0]

        return {
            'signature': signature,
            'revision': revision,
            'header_size': header_size,
            'crc32': crc32,
            'gpt_lba': gpt_lba,
            'backup_gpt_lba': backup_gpt_lba,
            'first_usable_lba': first_usable_lba,
            'last_usable_lba': last_usable_lba,
            'disk_guid': disk_guid,
            'partition_entry_start_lba': partition_etnry_start_lba,
            'number_of_partition_entries': number_of_partition_entries,
            'size_of_partition_entry': size_of_partition_entry,
            'crc32_of_partition_array': crc32_of_partition_array
        }

    def parse_entry(self, entry):
        partition_type_guid = uuid.UUID(bytes=entry[0:16])
        unique_partition_guid = uuid.UUID(bytes=entry[16:32])
        lba = struct.unpack_from("<Q", entry, 32)[0]
        size = struct.unpack_from("<Q", entry, 40)[0] - lba + 1
        flags = entry[48:56]
        name = entry[56:128].decode('utf-16')

        if partition_type_guid == self.UNUSED_GUID:
            return None

        return {
            'partition_type_guid': partition_type_guid,
            'unique_partition_guid': unique_partition_guid,
            'lba': lba,
            'size': size,
            'flags': flags,
            'name': name
        }

    def parse_entries(self, block, entry_size):
        block_size = len(block)

        partitions = []
        for i in range(int(block_size/entry_size)):
            entry = block[i*entry_size:(i+1)*entry_size]
            partition = self.parse_entry(entry)
            if partition:
                partitions.append(partition)
            else:
                break
        
        return partitions

    def parse(self):
        data = self.drive.read(1)
        header = self.parse_header(data)
        print(header)

        needed_sector_count = int(header['size_of_partition_entry'] * header['number_of_partition_entries'] / 512)

        data = self.drive.read(header['partition_entry_start_lba'], needed_sector_count)
        return self.parse_entries(data, header['size_of_partition_entry'])


if __name__ == '__main__':
    # Windows : "\\\\.\\PhysicalDrive%d"
    # Linux : "/dev/sda"

    drive = Drive(sys.argv[1])
    finder = GPTFinder(drive)
    parititons = finder.parse()
    for partition in parititons:
        print(partition)
