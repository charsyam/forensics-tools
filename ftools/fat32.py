import sys
import struct
from vfs import VFS
from vdrive import Drive
from vfile import BlockFile
from schema import Schema
from utils import Utils
import pprint


def to_decode(byte_arr, decoding):
    if len(byte_arr) == 0:
        return ""

    try:
        return byte_arr.decode(decoding)
    except:
        return byte_arr

def to_ucs2_le(byte_arr):
    return to_decode(byte_arr, 'utf-16-le')

def to_euc_kr(byte_arr):
    return to_decode(byte_arr, 'euc-kr')


class FAT32(VFS):
    def __init__(self, drive):
        super(FAT32, self).__init__(drive)
        self.get_vbr_info()

    def get_vbr_info(self):
        data = self.drive.read(0)
        self.vbr = self.parse_vbr(data) 
        self.rsc = self.vbr["reserved_sector_count"]
        nfats = self.vbr["nfats"]
        self.fat_size = self.vbr["fat_size"]
        self.bps = self.vbr["bps"]
        self.spc = self.vbr["spc"]
        self.fds = self.rsc + self.fat_size * nfats

    def get_fat_info(self, start, fat_idx=0):
        base_sector = self.rsc + fat_idx * self.fat_size
        fps = int(self.bps / 4)

        target = start
        needed_sector = -1
        base = 0
        data = None

        fat = []

        v = start

        while v != 0x0FFFFFFF:
            fat.append(v)
            target = v
            new_needed_sector = int(target / fps)
            if needed_sector != new_needed_sector:
                needed_sector = new_needed_sector
                base = fps * needed_sector
                data = self.drive.read(base_sector + needed_sector)

            loc = target % fps
            v = struct.unpack("<I", data[loc * 4:loc * 4 + 4])[0]            

        return self.fat_to_extends(fat)

    def fat_to_extends(self, fat):
        current = -1
        start = -1
        count = 1

        extends = []

        for i in fat:
            if start == -1:
                start = i
                current = i
                count = 1
            elif current + 1 == i:
                current = i
                count += 1
            else:
                extends.append((start, count))
                start = i
                current = i
                count = 1
                
        # last 
        extends.append((start, count))
        return extends                

    def parse_vbr(self, data):
        vbr_desc = Schema()
        vbr_desc.add("oem_name", 3, 8, dtype="str")
        vbr_desc.add("bps", 11, 2)
        vbr_desc.add("spc", 13, 1)
        vbr_desc.add("reserved_sector_count", 14, 2)
        vbr_desc.add("nfats", 16, 1)
        vbr_desc.add("total_sectors", 32, 4)
        vbr_desc.add("fat_size", 36, 4)
        vbr_desc.add("root_dir", 44, 4)
        vbr_desc.add("fstype", 82, 8, dtype="str")

        return Utils.schema_to_map(vbr_desc, data, endian=Utils.LITTLE_ENDIAN)

    def read(self, cluster, count=1):
        if (cluster < 2):
            raise Exception("Not Supported Cluster Number: " + str(cluster))

        rc = cluster - 2
        return self.drive.read(self.fds + self.spc * rc, count * self.spc)

    def list(self, cluster):
        fats = fat32.get_fat_info(cluster)
        data = bytes()
        for cluster, count in fats:
            data += self.read(cluster, count)

        l = self.parse_list(data)
        return l

    def strip(self, ucs_str):
        l = len(ucs_str) 
        for i in range(l):
            if ucs_str[i] == u'\uffff' or ucs_str[i] == u'\x00':
                return ucs_str[:i]

        return ucs_str

    def _parse_directory_entry(self, data, lfn):
        desc = Schema()
        desc.add("name", 0, 8, dtype="str", transform=to_euc_kr)
        desc.add("ext", 8, 3, dtype="str")
        desc.add("attr", 11, 1)
        desc.add("ctime_tenth", 13, 1)
        desc.add("ctime", 14, 2)
        desc.add("cdate", 16, 2)
        desc.add("adate", 18, 2)
        desc.add("fat_high", 20, 2)
        desc.add("wtime", 22, 2)
        desc.add("wdate", 24, 2)
        desc.add("fat_low", 26, 2)
        desc.add("size", 28, 4)

        entry = Utils.schema_to_map(desc, data, endian=Utils.LITTLE_ENDIAN)
        entry["cluster"] = entry["fat_high"] << 16 | entry["fat_low"]

        if lfn:
            entry["sname"] = entry["name"]
            entry["name"] = lfn

        return entry

    def _parse_directory_entry_lfn(self, data, lfn):
        desc = Schema()
        desc.add("order", 0, 1)
        desc.add("name1", 1, 10, dtype="str", transform=to_ucs2_le)
        desc.add("name2", 14, 12, dtype="str", transform=to_ucs2_le)
        desc.add("name3", 28, 4, dtype="str", transform=to_ucs2_le)

        entry = Utils.schema_to_map(desc, data, endian=Utils.LITTLE_ENDIAN)
        name1 = self.strip(entry["name1"])
        name2 = self.strip(entry["name2"])
        name3 = self.strip(entry["name3"])

        del entry["name1"]
        del entry["name2"]
        del entry["name3"]

        extra = ""
        if lfn:
            extra = lfn

        entry["name"] = name1 + name2 + name3 + extra
        return entry

    def parse_list(self, data):
        s = len(data)
        old_lfn = False
        files = []

        lfn = ""

        for i in range(0, s, 32):
            d = data[i:i+32]
            is_lfn = d[11] & 0x0F is 0x0F

            c = struct.unpack("<QQQQ", d)
            if c[0] == 0 and c[1] == 0 and c[2] == 0 and c[3] == 0:
                break

            if not is_lfn:
                entry = self._parse_directory_entry(d, lfn)
                files.append(entry)
                lfn = ""
            else:
                entry = self._parse_directory_entry_lfn(d, lfn)
                lfn = self._get_lfn(entry)

        return files

    def _get_lfn(self, entry):
        return entry["name"]


if __name__ == '__main__':
    vdrive = Drive(sys.argv[1])   
    fat32 = FAT32(vdrive)
    files = fat32.list(2)
    for f in files:
        pprint.pprint(f)
