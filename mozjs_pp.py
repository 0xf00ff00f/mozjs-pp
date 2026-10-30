import ctypes

JSVAL_TAG_SHIFT = 47

# JSValueType
JSVAL_TYPE_DOUBLE = 0x00
JSVAL_TYPE_INT32 = 0x02
JSVAL_TYPE_NULL = 0x04
JSVAL_TYPE_UNDEFINED = 0x06
JSVAL_TYPE_BOOLEAN = 0x08
JSVAL_TYPE_MAGIC = 0x0a
JSVAL_TYPE_PRIVATE_GCTHING = 0x0b
JSVAL_TYPE_OBJECT = 0x0c
JSVAL_TYPE_BIGINT = 0x0d
JSVAL_TYPE_STRING = 0x0e
JSVAL_TYPE_SYMBOL = 0x0f

# JSValueTag
JSVAL_TAG_MAX_DOUBLE = 0x1fff0
JSVAL_TAG_INT32 = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_INT32
JSVAL_TAG_UNDEFINED = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_UNDEFINED
JSVAL_TAG_NULL = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_NULL
JSVAL_TAG_BOOLEAN = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_BOOLEAN
JSVAL_TAG_MAGIC = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_MAGIC
JSVAL_TAG_STRING = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_STRING
JSVAL_TAG_SYMBOL = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_SYMBOL
JSVAL_TAG_PRIVATE_GCTHING = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_PRIVATE_GCTHING
JSVAL_TAG_BIGINT = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_BIGINT
JSVAL_TAG_OBJECT = JSVAL_TAG_MAX_DOUBLE | JSVAL_TYPE_OBJECT

JSVAL_SHIFTED_TAG_MAX_DOUBLE = (JSVAL_TAG_MAX_DOUBLE << JSVAL_TAG_SHIFT) | 0xFFFFFFFF

class JSValuePrinter:
    _JSVAL_TAG_TYPE = {
        JSVAL_TAG_INT32: "Int32",
        JSVAL_TAG_UNDEFINED: "Undefined",
        JSVAL_TAG_NULL: "Null",
        JSVAL_TAG_BOOLEAN: "Boolean",
        JSVAL_TAG_MAGIC: "Magic",
        JSVAL_TAG_STRING: "String",
        JSVAL_TAG_SYMBOL: "Symbol",
        JSVAL_TAG_PRIVATE_GCTHING: "PrivateGCThing",
        JSVAL_TAG_BIGINT: "BigInt",
        JSVAL_TAG_OBJECT: "Object",
    }

    def __init__(self, val):
        self._val = val

    def to_string(self):
        bits = int(self._val['asBits_'])
        is_double = bits <= JSVAL_SHIFTED_TAG_MAX_DOUBLE
        tag_name = None
        value = None
        if is_double:
            tag_name = 'Double'
            value = ctypes.c_double.from_buffer(ctypes.c_uint64(bits)).value # thanks clanker
        else:
            tag = bits >> JSVAL_TAG_SHIFT
            tag_name = self._JSVAL_TAG_TYPE.get(tag, 'Unknown')
            if tag == JSVAL_TAG_INT32:
                value = bits & ((1 << 32) - 1)
            elif tag == JSVAL_TAG_BOOLEAN:
                b = bits & ((1 << JSVAL_TAG_SHIFT) - 1)
                value = 'false' if b == 0 else 'true'
            elif tag == JSVAL_TAG_STRING:
                # StringFlags
                LATIN1_CHARS_BIT = 1 << 10
                INLINE_CHARS_BIT = 1 << 6
                shifted_tag = JSVAL_TAG_STRING << JSVAL_TAG_SHIFT;
                addr = bits ^ shifted_tag
                jsstring_ptr = gdb.Value(addr).cast(gdb.lookup_type('JSString').pointer())
                cell_header = jsstring_ptr['header_']['value_']
                flags = cell_header & 0xffffffff                    # CellWithLengthAndFlags::headerFlagsField
                has_latin1_chars = (flags & LATIN1_CHARS_BIT) != 0  # JSString::hasLatin1Chars
                is_inline = (flags & INLINE_CHARS_BIT) != 0         # JSString::isInline
                length = cell_header >> 32                          # CellWithLengthAndFlags::headerLengthField
                if is_inline:
                    if has_latin1_chars:
                        data = jsstring_ptr['d']['inlineStorageLatin1']
                    else:
                        data = jsstring_ptr['d']['inlineStorageTwoByte']
                else:
                    if has_latin1_chars:
                        data = jsstring_ptr['d']['s']['u2']['nonInlineCharsLatin1']
                    else:
                        data = jsstring_ptr['d']['s']['u2']['nonInlineCharsTwoByte']
                string = data.string(length=length)
                value = f'"{string}"'
        result = tag_name
        if value is not None:
            result += f"({value})"
        return result

def mozjs_pp_func(val):
    type_tag = val.type.unqualified().strip_typedefs().tag
    if type_tag == 'JS::Value':
        return JSValuePrinter(val)
    return None

gdb.pretty_printers.append(mozjs_pp_func)
