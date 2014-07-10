#!/usr/bin/env python

from logging import getLogger
from struct import Struct

PKT_HELLO       = 0x00
PKT_HELLOACK    = 0x01  # unused
PKT_COMMIT      = 0x02
PKT_DHPART11    = 0x03
PKT_DHPART12    = 0x04
PKT_DHPART13    = 0x05
PKT_DHPART14    = 0x06
PKT_DHPART15    = 0x07
PKT_DHPART21    = 0x08
PKT_DHPART22    = 0x09
PKT_DHPART23    = 0x0a
PKT_DHPART24    = 0x0b
PKT_DHPART25    = 0x0c
PKT_DHPART2     = 0x0d
PKT_CONFIRM1    = 0x0e
PKT_CONFIRM2    = 0x0f
PKT_CODEC2      = 0x10

ULONG_PACK = Struct('!Q').pack

PKT_CODEC2_CHR = chr(PKT_CODEC2)

class VoiZPacketFactory():

    def __init__(self, cache, mac):
        self.logger = getLogger('pkt-factory')
        self.cache = cache
        self.mac = mac

    def gen_pkt_payload_hello(self):
        return chr(PKT_HELLO) + self.mac.h3 + self.cache.getZID()

    def gen_pkt_hello(self):
        payload = self.gen_pkt_payload_hello()
        return payload + self.mac.hmac_h2(payload)[:8]

    def dct_pkt_hello(self, pkt):
        return pkt[1:33], pkt[33:45], pkt[45:53]

    def gen_pkt_payload_commit(self):
        return chr(PKT_COMMIT) + self.mac.h2 + self.cache.getZID() + self.mac.generateCounterSuffix()

    def gen_pkt_commit(self):
        payload = self.gen_pkt_payload_commit()
        return payload + self.mac.hmac_h1(payload)[:8]

    def dct_pkt_commit(self, pkt):
        return pkt[1:33], pkt[33:45], pkt[45:53], pkt[53:61]

    def gen_pkt_payload_dhpart1(self):
        return self.mac.h1 + ('\x00' * 16) + self.mac.packedPublicKey()

    def gen_pkts_dhpart1(self):
        payload = self.gen_pkt_payload_dhpart1()
        payload += self.mac.hmac_h0(payload)[:8]
        return [
            chr(PKT_DHPART11) + payload[0:63],
            chr(PKT_DHPART12) + payload[63:126],
            chr(PKT_DHPART13) + payload[126:189],
            chr(PKT_DHPART14) + payload[189:252],
            chr(PKT_DHPART15) + payload[252:312],
        ]

    def gen_pkts_dhpart2(self):
        payload = self.gen_pkt_payload_dhpart1()
        payload += self.mac.hmac_h0(payload)[:8]
        return [
            chr(PKT_DHPART21) + payload[0:63],
            chr(PKT_DHPART22) + payload[63:126],
            chr(PKT_DHPART23) + payload[126:189],
            chr(PKT_DHPART24) + payload[189:252],
            chr(PKT_DHPART25) + payload[252:312],
        ]

    def dct_pkts_dhpart1(self, pkt):
        return pkt[1:33], pkt[33:41], pkt[41:49], pkt[49:305], pkt[305:313]

    def gen_pkt_confirm1(self):
        # encrypt h0
        enc_h0 = self.mac.encrypt(self.mac.h0)
        confirmmackey = self.mac.hmac_s0('Responder HMAC key')
        confirmmac = self.mac.getHMAC(confirmmackey, enc_h0)
        return chr(PKT_CONFIRM1) + confirmmac[:8] + enc_h0

    def gen_pkt_confirm2(self):
        # encrypt h0
        enc_h0 = self.mac.encrypt(self.mac.h0)
        confirmmackey = self.mac.hmac_s0('Initiator HMAC key')
        confirmmac = self.mac.getHMAC(confirmmackey, enc_h0)
        return chr(PKT_CONFIRM2) + confirmmac[:8] + enc_h0

    def dct_pkt_confirm1(self, pkt):
        return pkt[1:9], pkt[9:41]

    def gen_pkt_codec2(self, payload):
        return PKT_CODEC2_CHR + ULONG_PACK(self.mac.encctr) + self.mac.encrypt(PKT_CODEC2_CHR + payload)