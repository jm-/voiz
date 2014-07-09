#!/usr/bin/env python

from logging import getLogger
from struct import Struct

PKT_HELLO       = 0x00
PKT_HELLOACK    = 0x01
PKT_COMMIT      = 0x02
PKT_DHPART1     = 0x03
PKT_DHPART2     = 0x04
PKT_CONFIRM1    = 0x05
PKT_CONFIRM2    = 0x06

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