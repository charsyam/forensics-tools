import struct

class Utils:
    LITTLE_ENDIAN=0
    BIG_ENDIAN=1
    SIZE_TO_UNPACK = {
        LITTLE_ENDIAN: {
            1: "<B",
            2: "<H",
            4: "<I",
            8: "<Q"
        },
        BIG_ENDIAN: {
            1: ">B",
            2: ">H",
            4: ">I",
            8: ">Q"
        },

    }

    @staticmethod
    def combine16_32(hi, lo):
        return (hi << 32) | lo

    @staticmethod
    def _type_to_map(column, length, buf, endian, base_offset):
        v = ""

        offset = column["offset"] + base_offset
        dtype = column["type"]

        if length in Utils.SIZE_TO_UNPACK[endian] and dtype == "int":
            fmt = Utils.SIZE_TO_UNPACK[endian][length]
            v = struct.unpack_from(fmt, buf, offset)[0]
        elif dtype == "schema":
            s = column["schema"] 
            v = Utils.schema_to_map(s, buf, endian=endian, base_offset = offset)
        else:
            v = buf[offset:offset+length]

        if column["transform"] is not None:
            v = column["transform"](v)

        return column["label"], v


    @staticmethod
    def _default_len(v):
        return v

    @staticmethod
    def _column_length(column, m):
        len_func = column["len_func"] if column["len_func"] else Utils._default_len

        if isinstance(column["length"], int):
            length = column["length"]
        elif isinstance(column["length"], str):
            length = m[column["length"]]
        else:
            raise Exception("No Column Length type")

        return len_func(length)

    @staticmethod
    def schema_to_map(schema, buf, endian=0, base_offset=0):
        v = {}
        sub_offset = 0
            
        for column in schema.schema:
            length = Utils._column_length(column, v)
            k, value = Utils._type_to_map(column, length, buf,
                                          endian=endian, base_offset=base_offset)
            if k in v and type(v[k]) != list:
                tmp_v = v[k]
                v[k] = []
                v[k].append(tmp_v)
                v[k].append(value)
            elif k in v and type(v[k]) == list:
                v[k].append(value)
            else: 
                v[k] = value

        return v
