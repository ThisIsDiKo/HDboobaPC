#from Crypto.Cipher import AES
import Crypto.Cipher.AES
from binascii import hexlify, unhexlify
key = unhexlify('2b7e151628aed2a6abf7158809cf4f3c')
IV = unhexlify('000102030405060708090a0b0c0d0e0f')