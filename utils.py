
def serialize_32bit(number, order='little-endian'):
    b4 = (number & 0xFF000000) >> 24
    b3 = (number & 0x00FF0000) >> 16
    b2 = (number & 0x0000FF00) >> 8
    b1 = (number & 0x000000FF)

    if order == 'little-endian':
        return [b1, b2, b3, b4]
    else:
        return [b4, b3, b2, b1]


def generate_crc32_table():
    custom_crc_table = []
    _poly = 0x04C11DB7

    for i in range(256):
        c = i << 24

        for j in range(8):
            c = (c << 1) ^ _poly if (c & 0x80000000) else c << 1

        custom_crc_table[i] = c & 0xffffffff

    return custom_crc_table

def custom_crc32(buf):
    custom_crc_table = generate_crc32_table()
    crc = 0xffffffff
    for integer in buf:
        b = serialize_32bit(integer, order='big-endian')
        for byte in b:
            crc = ((crc << 8) & 0xffffffff) ^ custom_crc_table[(crc >> 24) ^ byte]
    return crc

def add_preamb_and_crc(buf):
    preamb = []

    if len(buf) % 4 != 0:
        return False

    crc = custom_crc32(buf)
    crc_bytes = serialize_32bit(crc)

    preamb.extend(buf)
    preamb.extend(crc_bytes)

    return preamb

