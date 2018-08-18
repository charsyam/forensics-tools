import sys
import struct
from vfs import VFS
from vdrive import Drive
from vfile import BlockFile
from schema import Schema
from utils import Utils


ATTR_DATA = 0x80
ATTR_INDEX_ALLOCATION = 0x90

def to_decode(byte_arr, decoding):
    if len(byte_arr) == 0:
        return ""

    return byte_arr.decode(decoding)

def to_ucs2_le(byte_arr):
    return to_decode(byte_arr, 'utf-16-le')

def to_euc_kr(byte_arr):
    return to_decode(byte_arr, 'euc-kr')


class NTFS(VFS):
    def __init__(self, drive):
        super(NTFS, self).__init__(drive)
        self.get_vbr_info()

    def get_vbr_info(self):
        data = self.drive.read(0)
        self.vbr = self.parse_vbr(data) 
        self.bps = self.vbr["bps"]
        self.spc = self.vbr["spc"]
        self.mft = self.vbr["mft"]
        self.size = self.vbr["total_sectors"]
        self.mftsize = self.get_mft_entry_size(self.vbr["mft_entry_size"])
        mft0 = self.parse_mft(self.mft)
        bfile = self.get_attr_datafile(mft0, ATTR_DATA, 0)
        print(self.vbr)

    def get_mft_entry_size(self, v):
        if v < 0x80:
            return self.spc * self.bps * v
        else:
            return pow(2, 256-v)

    def parse_vbr(self, data):
        vbr_desc = Schema()
        vbr_desc.add("oem_name", 3, 8, dtype="str")
        vbr_desc.add("bps", 11, 2)
        vbr_desc.add("spc", 13, 1)
        vbr_desc.add("total_sectors", 40, 8)
        vbr_desc.add("mft", 48, 8)
        vbr_desc.add("mftmirr", 56, 4)
        vbr_desc.add("mft_entry_size", 64, 1)
        vbr_desc.add("index_record_size", 68, 1)

        return Utils.schema_to_map(vbr_desc, data, endian=Utils.LITTLE_ENDIAN)

    def parse_mft(self, start_mft):
        data = self.read(start_mft)
        mft_desc = Schema()
        mft_desc.add("signature", 0, 4, dtype="str")
        mft_desc.add("offset_fixup_array", 4, 2)
        mft_desc.add("count_of_fixup_array", 6, 2)
        mft_desc.add("lsn", 8, 8)
        mft_desc.add("seq_value", 16, 2)
        mft_desc.add("hard_link_count", 18, 2)
        mft_desc.add("offset_first_attr", 20, 2)
        mft_desc.add("flags", 22, 2)
        mft_desc.add("used_size_of_mft_etnry", 24, 4)
        mft_desc.add("allocated_size_of_mft_entry", 28, 4)
        mft_desc.add("file_ref_to_base", 32, 8)
        mft_desc.add("next_attr_id", 40, 2)

        mft = Utils.schema_to_map(mft_desc, data, endian=Utils.LITTLE_ENDIAN)

        fixup_start = 510
        fixup_array = mft["offset_fixup_array"]+2
        for i in range(mft["count_of_fixup_array"]):
            data[fixup_start] = data[fixup_array]
            data[fixup_start+1] = data[fixup_array+1]
            fixup_start += 512

        return self.parse_attrs(data, mft["offset_first_attr"])
            
    def parse_attr_header(self, data, offset):
        attr_desc = Schema()
        attr_desc.add("attr_type_id", offset, 4)
        attr_desc.add("length", offset+4, 4)
        attr_desc.add("non-resident", offset+8, 1)
        attr_desc.add("name_len", offset+9, 1)
        attr_desc.add("offset_name", offset+10, 2)
        attr_desc.add("flags", offset+12, 2)
        attr_desc.add("attr_id", 14, 2)

        attr = Utils.schema_to_map(attr_desc, data, endian=Utils.LITTLE_ENDIAN)
        return attr

    def copy_map(self, src, tar):
        for key in src.keys():
            tar[key] = src[key]

    def parse_resident_attr(self, data, offset, attr):
        attr_desc = Schema()
        attr_desc.add("content_size", offset+16, 4)
        attr_desc.add("content_offset", offset+20, 2)
        attr_desc.add("indexed_flag", offset+22, 1)

        attr2 = Utils.schema_to_map(attr_desc, data, endian=Utils.LITTLE_ENDIAN)
        self.copy_map(attr2, attr)
 
        return attr
        
    def parse_non_resident_attr(self, data, offset, attr):
        attr_desc = Schema()
        attr_desc.add("start_vcn", offset+16, 8)
        attr_desc.add("end_vcn", offset+24, 8)
        attr_desc.add("runlists_offset", offset+32, 2)
        attr_desc.add("comp_unit_size", offset+34, 2)
        attr_desc.add("alloc_size", offset+40, 8)
        attr_desc.add("real_size", offset+48, 8)
        attr_desc.add("init_size", offset+56, 8)

        attr2 = Utils.schema_to_map(attr_desc, data, endian=Utils.LITTLE_ENDIAN)
        self.copy_map(attr2, attr)

        runlists = self.parse_runlists(data, offset + attr2["runlists_offset"])
        attr["runlists"] = runlists
        return attr

    def parse_runlists_value(self, v):
        k = 1
        ret = 0
        for i in v:
            ret += i * k
            k *= 256

        return ret

    def parse_runlists(self, data, offset):
        runlists = []
        pos = offset
        base_offset = 0
        while True:
            if data[pos] == 0:
                break
            offset_size = (data[pos] & 0xF0) >> 4
            len_size = (data[pos] & 0x0F)
            
            l = self.parse_runlists_value(data[pos+1:pos+1+len_size])
            offset = self.parse_runlists_value(data[pos+1+len_size:pos+1+len_size+offset_size])
            base_offset += offset

            pos = pos + 1 + (offset_size + len_size)
            runlists.append((base_offset, l))

        return runlists

    def get_attr_datafile(self, attrs, attr_type_id, attr_id):
        for attr in attrs:
            if attr['attr_type_id'] == attr_type_id and attr['attr_id'] == attr_id:
                return self.get_runlists_file(attr['runlists'])

        raise Exception("No attr ({}:{})".format(attr_type_id, attr_id))

    def get_runlists_file(self, runlists):
        return BlockFile(self, -1, runlists)

    def parse_index_allocation(self, data, attr):
        import pdb; pdb.set_trace()
        datafile = self.get_runlists_file(attr['runlists'])

    def _parse_attr(self, data, attr):
        if attr["attr_type_id"] == ATTR_INDEX_ALLOCATION:
            self.parse_index_allocation(data, attr)
        
    def parse_attrs(self, data, offset):
        attrs = []
        while True:
            attr = self.parse_attr_header(data, offset)
            if attr["length"] == 0:
                break

            if attr["non-resident"] == 0:
                self.parse_resident_attr(data, offset, attr)
            else:
                self.parse_non_resident_attr(data, offset, attr)

            self._parse_attr(data, attr)
            attrs.append(attr)
            offset += attr["length"]

        return attrs

    def read(self, cluster, count=1):
        return bytearray(self.drive.read(self.spc * cluster, count * self.spc))


if __name__ == '__main__':
    vdrive = Drive(sys.argv[1])   
    ntfs = NTFS(vdrive)
