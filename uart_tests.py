import serial
import time

custom_crc_table = {}

def generate_crc32_table(_poly):
    global custom_crc_table

    for i in range(256):
        c = i << 24

        for j in range(8):
            c = (c << 1) ^ _poly if (c & 0x80000000) else c << 1

        custom_crc_table[i] = c & 0xffffffff


def int_to_bytes(i):
    return [(i >> 24) & 0xFF, (i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF]

def custom_crc32(buf):
    global custom_crc_table
    crc = 0xffffffff

    for integer in buf:
        b = int_to_bytes(integer)

        for byte in b:
            crc = ((crc << 8) & 0xffffffff) ^ custom_crc_table[(crc >> 24) ^ byte]

    return crc




poly = 0x04C11DB7

port_num = 'COM9'
port_baudrate = 115200
port_stopbits = serial.STOPBITS_ONE
port_parity = serial.PARITY_NONE
port_timeout = 2


preamb = [0x61, 0x62, 0x63, 0x64]

serial_arg = dict(port=port_num,
                  baudrate=port_baudrate,
                  topbits=port_stopbits,
                  parity=port_parity,
                  timeout=port_timeout
                  )
connection = None
try:
    # connection = serial.Serial(**serial_arg)

    connection = serial.Serial(
                            port='COM9',
                            baudrate=115200,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            bytesize=serial.EIGHTBITS,
                            timeout=0)
except:
    print("error opening com port")


def deserialize_uint32(buf):
    if len(buf) % 4 != 0:
        print("buf is not % 4")
        return None
    v = []
    for i in range(0, len(buf), 4):
        o = buf[i]
        o += buf[i + 1] << 8
        o += buf[i + 2] << 16
        o += buf[i + 3] << 24
        v.append(o)
    return v

def serialize_crc(crc):
    b4 = (custom_crc & 0xFF000000) >> 24
    b3 = (custom_crc & 0x00FF0000) >> 16
    b2 = (custom_crc & 0x0000FF00) >> 8
    b1 = (custom_crc & 0x000000FF)
    return [b1, b2, b3, b4]


if connection:
    buf = [0x97, 0x68, 0x00, 0x00]
    #buf = [170, 85, 16, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    generate_crc32_table(poly)

    v = deserialize_uint32(buf)
    custom_crc = custom_crc32(v)
    crc = serialize_crc(custom_crc)
    print("Custom crc {0}, [{1}, {2}, {3}, {4}]".format(custom_crc, hex(crc[0]), hex(crc[1]), hex(crc[2]), hex(crc[3])))


    print('writing to com port')
    msg = preamb
    msg.extend(buf)
    msg.extend(crc)

    bMsg = bytearray(msg)
    print([i for i in bMsg])

    connection.reset_input_buffer()
    try:
        connection.write(bMsg)
    except:
        print('error while sending msg')

    time.sleep(0.5)
    incomingBytes = []
    while connection.inWaiting() > 0:
        incomingBytes.append(connection.read(1))

    print(incomingBytes)

    connection.close()

    l = [int.from_bytes(b, 'big') for b in incomingBytes]
    print(l)


    def parse_msg(msg):
        preamb = [0x45, 0xA3, 0x7E, 0x81]
        print(preamb)
        start_preamb_index = 0

        for i in range(len(msg)):
            if msg[i] == preamb[0] and msg[i+1] == preamb[1] and msg[i+2] == preamb[2] and msg[i+3] == preamb[3]:
                start_preamb_index = i
                break
        if start_preamb_index >0:
            utf_msg = msg[0:start_preamb_index]
            byte_msg = msg[start_preamb_index+4:]

            print('Parsed MSG:')
            print(''.join(chr(o) for o in utf_msg))
            print('Unparsed msg:')
            print(byte_msg)

            command = byte_msg[0]
            n_command = byte_msg[1]
            if command == (n_command ^ 0xff):
                print("command correct")

            param_len = byte_msg[2] + (byte_msg[3] << 8)
            print("command len: {0}".format(param_len))

            cmd_crc_b = byte_msg[4+param_len:8+param_len]
            cmd_crc = deserialize_uint32(cmd_crc_b)[0]
            cmd_uint32 = deserialize_uint32(byte_msg[:4+param_len])
            real_crc = custom_crc32(cmd_uint32)

            print('got crc: {0} [{1}]'.format(cmd_crc, cmd_crc_b))
            print('calculate crc: {}'.format(real_crc))

            body = []

            if cmd_crc == real_crc:
                body = byte_msg[4:4+param_len]
            else:
                print('crc not matched')
                return None

            print('Размер тела команды: {0}'.format(len(body)))

            if command == 0x97:
                print('Получен ответ на запос информации')
                print('Device ID: {0}'.format([hex(i) for i in body[:12]]))
                print('Dev id: {0}, Rev id: {1}'.format(hex((body[12] + (body[13] << 8)) & 0xfff),
                      hex(body[14] + (body[15] << 8))))
                print('Размер Флеш памяти: {0} кбайт'.format(body[16] + (body[17] << 8)))
                print('Версия загрузчика: {0}'.format(hex(body[18] + (body[19] << 8))))
                print('Размер приемного буфера: {0} байт'.format(body[20] + (body[21] << 8) + (body[22] << 16) + (body[23] << 24)))
                print('Адрес начала программируемой памяти: {0}'.format(hex(body[24] + (body[25] << 8) + (body[26] << 16) + (body[27] << 24))))
                print('Адрес начала программы: {0}'.format(hex(body[28] + (body[29] << 8) + (body[30] << 16) + (body[31] << 24))))
            else:
                print('Получена неизвестная команда')




        else:
            print('Parsed MSG:')
            print(''.join(chr(o) for o in msg))
    parse_msg(l)



