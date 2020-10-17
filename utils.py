
def serialize_32bit(number, order='little-endian'):
    b4 = (number & 0xFF000000) >> 24
    b3 = (number & 0x00FF0000) >> 16
    b2 = (number & 0x0000FF00) >> 8
    b1 = (number & 0x000000FF)

    if order == 'little-endian':
        return [b1, b2, b3, b4]
    else:
        return [b4, b3, b2, b1]

def serialize_16bit(number, order='little-endian'):
    b2 = (number & 0x0000FF00) >> 8
    b1 = (number & 0x000000FF)

    if order == 'little-endian':
        return [b1, b2]
    else:
        return [b2, b1]

def deserialize_32bit(buf, order='little-endian'):
    if len(buf) % 4 != 0:
        return None
    v = []
    if order == 'little-endian':
        for i in range(0, len(buf), 4):
            o = buf[i]
            o += buf[i + 1] << 8
            o += buf[i + 2] << 16
            o += buf[i + 3] << 24
            v.append(o)
    else:
        for i in range(0, len(buf), 4):
            o = buf[i + 3]
            o += buf[i + 2] << 8
            o += buf[i + 1] << 16
            o += buf[i] << 24
            v.append(o)
    return v


def generate_crc32_table():
    custom_crc_table = {}
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
    buf_32bit = deserialize_32bit(buf)
    for integer in buf_32bit:
        b = serialize_32bit(integer, order='big-endian')
        for byte in b:
            crc = ((crc << 8) & 0xffffffff) ^ custom_crc_table[(crc >> 24) ^ byte]
    return crc

def add_preamb_and_crc(buf):
    preamb = [97, 98, 99, 100]

    if len(buf) % 4 != 0:
        return None

    crc = custom_crc32(buf)
    crc_bytes = serialize_32bit(crc)

    preamb.extend(buf)
    preamb.extend(crc_bytes)

    return preamb

def parse_msg(msg):
    ness_preamb = [0x45, 0xA3, 0x7E, 0x81]
    start_preamb_index = -1
    for i in range(len(msg)):
        try:
            if msg[i] == ness_preamb[0] and \
                    msg[i + 1] == ness_preamb[1] and \
                    msg[i + 2] == ness_preamb[2] and \
                    msg[i + 3] == ness_preamb[3]:
                start_preamb_index = i
                break
        except:
            pass


    if start_preamb_index >= 0:
        if len(msg) - (start_preamb_index+1) < (4+4):
            return None
        byte_msg = msg[start_preamb_index + 4:]

        command = byte_msg[0]
        n_command = byte_msg[1]
        if command != (n_command ^ 0xff):
            print("command not correct")
            return None

        param_len = byte_msg[2] + (byte_msg[3] << 8)
        #print("param len is {0}, need {1}".format(param_len, len(msg) - (start_preamb_index+4+1+2+2)))
        if param_len > 0:
            if len(msg) - (start_preamb_index+4+4) < (param_len + 4):
                #print("wrong param number")
                return None

        #print("calculating crc")
        cmd_crc_b = byte_msg[4 + param_len:8 + param_len]
        #print("crc bytes: {0}".format(cmd_crc_b))
        cmd_crc = deserialize_32bit(cmd_crc_b)[0]
        #print("cmd crc: {0}".format(cmd_crc))

        real_bytes_for_crc = byte_msg[:4 + param_len]
        cmd_uint32 = deserialize_32bit(real_bytes_for_crc)
        #print('{0} --- {1}'.format(real_bytes_for_crc, cmd_uint32))

        real_crc = custom_crc32(real_bytes_for_crc)
        #print("crc real: {0}".format(real_crc))

        body = []
        if cmd_crc == real_crc:
            body = byte_msg[4:4 + param_len]
            print("crc is ok")
        else:
            print('crc not matched')
            endIndex = start_preamb_index + 4 + 4 + param_len + 4 - 1
            return {'type': 'crc error', 'endIndex': endIndex}

        result = {}
        print('Command number is: {0}'.format(hex(command)))
        if command == 0x97:
            # print('Получен ответ на запос информации')
            # print('Device ID: {0}'.format([hex(i) for i in body[:12]]))
            # print('Dev id: {0}, Rev id: {1}'.format(hex((body[12] + (body[13] << 8)) & 0xfff),
            #                                         hex(body[14] + (body[15] << 8))))
            # print('Размер Флеш памяти: {0} кбайт'.format(body[16] + (body[17] << 8)))
            # print('Версия загрузчика: {0}'.format(hex(body[18] + (body[19] << 8))))
            # print('Размер приемного буфера: {0} байт'.format(
            #     body[20] + (body[21] << 8) + (body[22] << 16) + (body[23] << 24)))
            # print('Адрес начала программируемой памяти: {0}'.format(
            #     hex(body[24] + (body[25] << 8) + (body[26] << 16) + (body[27] << 24))))
            # print('Адрес начала программы: {0}'.format(
            #     hex(body[28] + (body[29] << 8) + (body[30] << 16) + (body[31] << 24))))

            result['type'] = 'info'
            result['UID'] = body[:12]
            result['Dev ID'] = (body[12] + (body[13] << 8)) & 0xfff
            result['Rev ID'] = body[14] + (body[15] << 8)
            result['Flash Size'] = body[16] + (body[17] << 8)
            result['Version'] = body[18] + (body[19] << 8)
            result['Rec Buf Size'] = body[20] + (body[21] << 8) + (body[22] << 16) + (body[23] << 24)
            result['Memory Addr'] = body[24] + (body[25] << 8) + (body[26] << 16) + (body[27] << 24)
            result['Programm Addr'] = body[28] + (body[29] << 8) + (body[30] << 16) + (body[31] << 24)
        elif command == 0xC5:
            result['type'] = 'erase'
            result['size'] = param_len
            if param_len > 0:
                result['erased bytes'] = body[:4]
        elif command == 0x38:
            result['type'] = 'write'
            result['size'] = param_len
            if param_len > 0:
                result['address'] = deserialize_32bit(body[:4])[0]
        elif command == 0x33:
            result['type'] = 'crc check'
            result['size'] = param_len
            if param_len > 0:
                result['crc'] = deserialize_32bit(body[:4])[0]
        else:
            result['type'] = 'unknown command'
            print('Получена неизвестная команда')

        endIndex = start_preamb_index + 4 + 4 + param_len + 4 - 1
        result['endIndex'] = endIndex
        return result