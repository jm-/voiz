#!/usr/bin/env python

from logging import getLogger
from time import sleep, time as now

from .tx import tx_block, PAYLOAD_LEN
from .rx import rx_block
from .crypto import VoiZCache, VoiZMAC
from .protocol import *

ZERO = '\x00'
DELAY = 0.2
TIMEOUT = 15.0

class VoiZApp():

    def __init__(self, conf):
        self.logger = getLogger('app')
        self.conf = conf
        self.cache = VoiZCache()
        self.logger.info('Using ZID = 0x%s', self.cache.getZID().encode('hex'))
        self.mac = VoiZMAC()
        # instantiate packet factory
        self.pkt_factory = VoiZPacketFactory(self.cache, self.mac)

    def send_until_pkt(self, send_pkts, recv_pkt_id, wait_forever=False):
        send_pkts = [pkt.ljust(PAYLOAD_LEN, ZERO) for pkt in send_pkts]
        attempts = len(send_pkts) * TIMEOUT / DELAY
        while wait_forever or attempts > 0:
            for send_pkt in send_pkts:
                self.tx.send_pkt(send_pkt)
                # look for received packet
                recv_pkt = self.rx.recv_pkt()
                if recv_pkt:
                    print len(recv_pkt), repr(recv_pkt)
                if recv_pkt and ord(recv_pkt[0]) == recv_pkt_id:
                    return recv_pkt
                sleep(DELAY)
                attempts -= 1

    def wait_until_pkt(self, recv_pkt_id, wait_forever=False):
        attempts = TIMEOUT / DELAY
        while wait_forever or attempts > 0:
            recv_pkt = self.rx.recv_pkt()
            if recv_pkt:
                print len(recv_pkt), repr(recv_pkt)
            if recv_pkt and ord(recv_pkt[0]) == recv_pkt_id:
                return recv_pkt
            sleep(DELAY)
            attempts -= 1

    def _initiate(self):
        self.logger.debug('Starting initiation procedure...')

        self.logger.debug('Sending packet: PKT_HELLO')
        pkt_hello = self.pkt_factory.gen_pkt_hello()
        rhello_pkt = self.send_until_pkt([pkt_hello], PKT_HELLO)
        if not rhello_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_HELLO')
        # dissect fields
        (   rh3,
            rzid,
            rhellohmac
        ) = self.pkt_factory.dct_pkt_hello(rhello_pkt)
        self.logger.debug('Responder ZID: 0x%s', rzid.encode('hex'))

        # prepare commit packet
        icommit_pkt = self.pkt_factory.gen_pkt_commit()
        self.logger.debug('Sending packet: PKT_COMMIT')
        rdhpart11_pkt = self.send_until_pkt([icommit_pkt], PKT_DHPART11)
        if not rdhpart11_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART11')
        rdhpart12_pkt = self.wait_until_pkt(PKT_DHPART12)
        if not rdhpart12_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART12')
        rdhpart13_pkt = self.wait_until_pkt(PKT_DHPART13)
        if not rdhpart13_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART13')
        rdhpart14_pkt = self.wait_until_pkt(PKT_DHPART14)
        if not rdhpart14_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART14')
        rdhpart15_pkt = self.wait_until_pkt(PKT_DHPART15)
        if not rdhpart15_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART15')
        # dissect fields
        (   rh1,
            rs1iDr,
            rs2iDr,
            pvr,
            dhpart1mac
        ) = self.pkt_factory.dct_pkts_dhpart1(
            rdhpart11_pkt +
            rdhpart12_pkt[1:64] +
            rdhpart13_pkt[1:64] +
            rdhpart14_pkt[1:64] +
            rdhpart15_pkt[1:61]
        )
        # verify original HELLO packet
        rh2 = self.mac.getHash(rh1)
        if not self.mac.verifyPacketHMAC(rh2, rhello_pkt[:45], rhellohmac):
            self.logger.error('HMAC failed in responders HELLO packet')
            return False
        # verify hash chain components
        if not self.mac.verifyHash(rh2, rh3):
            self.logger.error('Hash chain verification failed: sha256(h2) != h3')
            return False


        dhpart2_pkts = self.pkt_factory.gen_pkts_dhpart2()

        # set parameters
        self.mac.setPartnerPublicKey(pvr)
        self.mac.setPackets(
            rhello_pkt[:53] +
            icommit_pkt +
            rdhpart11_pkt +
            rdhpart12_pkt +
            rdhpart13_pkt +
            rdhpart14_pkt +
            rdhpart15_pkt[:61] +
            ''.join(dhpart2_pkts)
        )
        self.mac.computeSecret(self.cache.getZID(), rzid)

        # prepare dhpart2 packets
        self.logger.debug('Sending packets for DH-part2')
        iconfirm1_pkt = self.send_until_pkt(dhpart2_pkts, PKT_CONFIRM1)





    def _respond(self):
        self.logger.debug('Starting response procedure...')

        ihello_pkt = self.wait_until_pkt(PKT_HELLO, True)
        if not ihello_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_HELLO')
        # dissect fields
        (   ih3,
            izid,
            ihellohmac
        ) = self.pkt_factory.dct_pkt_hello(ihello_pkt)
        self.logger.debug('Initiator ZID: 0x%s', izid.encode('hex'))

        # prepare hello packet
        rhello_pkt = self.pkt_factory.gen_pkt_hello()
        # wait for commitment
        self.logger.debug('Sending packet: PKT_HELLO')
        icommit_pkt = self.send_until_pkt([rhello_pkt], PKT_COMMIT)
        if not icommit_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_COMMIT')
        # dissect fields
        (   ih2,
            izid2,
            icounter_suffix,
            icommithmac
        ) = self.pkt_factory.dct_pkt_commit(icommit_pkt)
        assert izid == izid2
        # verify original HELLO packet
        if not self.mac.verifyPacketHMAC(ih2, ihello_pkt[:45], ihellohmac):
            self.logger.error('HMAC failed in initiators HELLO packet')
            return False
        # verify hash chain components
        if not self.mac.verifyHash(ih2, ih3):
            self.logger.error('Hash chain verification failed: sha256(h2) != h3')
            return False
        self.logger.debug('Valid PKT_COMMIT packet')
        self.mac.setCounterSuffix(icounter_suffix)

        # prepare dhpart1 packets
        dhpart1_pkts = self.pkt_factory.gen_pkts_dhpart1()
        self.logger.debug('Sending packets for DH-part1')
        idhpart21_pkt = self.send_until_pkt(dhpart1_pkts, PKT_DHPART21)
        if not idhpart21_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART21')
        idhpart22_pkt = self.wait_until_pkt(PKT_DHPART22)
        if not idhpart22_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART22')
        idhpart23_pkt = self.wait_until_pkt(PKT_DHPART23)
        if not idhpart23_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART23')
        idhpart24_pkt = self.wait_until_pkt(PKT_DHPART24)
        if not idhpart24_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART24')
        idhpart25_pkt = self.wait_until_pkt(PKT_DHPART25)
        if not idhpart25_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_DHPART25')
        # dissect fields
        (   ih1,
            rs1iDi,
            rs2iDi,
            pvi,
            dhpart2mac
        ) = self.pkt_factory.dct_pkts_dhpart1(
            idhpart21_pkt +
            idhpart22_pkt[1:64] +
            idhpart23_pkt[1:64] +
            idhpart24_pkt[1:64] +
            idhpart25_pkt[1:61]
        )
        # verify COMMIT packet
        if not self.mac.verifyPacketHMAC(ih1, icommit_pkt[:53], icommithmac):
            self.logger.error('HMAC failed in initiators COMMIT packet')
            return False
        # verify hash chain components
        if not self.mac.verifyHash(ih1, ih2):
            self.logger.error('Hash chain verification failed: sha256(h1) != h2')
            return False
        # set parameters
        self.mac.setPartnerPublicKey(pvi)
        self.mac.setPackets(
            rhello_pkt +
            icommit_pkt[:61] +
            ''.join(dhpart1_pkts) +
            idhpart21_pkt +
            idhpart22_pkt +
            idhpart23_pkt +
            idhpart24_pkt +
            idhpart25_pkt[:61]
        )
        self.mac.computeSecret(izid, self.cache.getZID())

    def run(self):
        # setup tx and rx classes
        self.logger.debug('Instantiating tx block...')
        self.tx = tx_block(
            self.conf.carrier,
            self.conf.sideband,
            self.conf.transition,
            self.conf.sps,
            self.conf.interpolation,
            self.conf.looutdev
        )
        self.logger.debug('Instantiating rx block...')
        self.rx = rx_block(
            self.conf.carrier,
            self.conf.sideband,
            self.conf.transition,
            self.conf.sps,
            self.conf.interpolation,
            self.conf.lomicdev
        )

        self.rx.start()
        self.tx.start()

        if self.conf.initiate:
            # initiate communication
            proceed = self._initiate()
        else:
            proceed = self._respond()

        if proceed:
            pass

        self.tx.stop()
        self.rx.stop()