import pytest
import struct
from ftools.mbr import TableEntry as MBRTableEntry

def test_table_entry():
    test_mbr_entry = [0x80, 0, 0, 1, 0x07, 1, 1, 1, 0, 0, 0, 0]
    entry = bytearray(test_mbr_entry)
    entry += struct.pack('<I', 1024)

    table = MBRTableEntry(entry)

    assert table.active == 0x80
    assert table.lba == 0
    assert table.size == 1024
