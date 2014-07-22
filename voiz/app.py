#!/usr/bin/env python

from logging import getLogger
from time import sleep, time as now

from .c2 import Codec2Source, Codec2Sink
from .tx import tx_block, PAYLOAD_LEN
from .rx import rx_block
from .crypto import VoiZCache, VoiZMAC, InvalidHMACException
from .protocol import *

ZERO = '\x00'
DELAY = 0.2
TIMEOUT = 15.0
BACKOFF = range(5)

class VoiZApp():

    def __init__(self, conf):
        self.logger = getLogger('app')
        self.conf = conf
        self.cache = VoiZCache()
        self.logger.info('Using ZID = 0x%s', self.cache.getZID().encode('hex'))
        self.mac = VoiZMAC()
        # instantiate packet factory
        self.pkt_factory = VoiZPacketFactory(self.cache, self.mac)

        self.send_until_pkt = self._send_until_pkt_backoff if conf.backoff else self._send_until_pkt

    def send(self, send_pkt, count=1):
        send_pkt = send_pkt.ljust(PAYLOAD_LEN, ZERO)
        self.tx.send_pkt(send_pkt)
        count -= 1
        while count > 0:
            sleep(DELAY)
            self.tx.send_pkt(send_pkt)
            count -= 1

    def _send_until_pkt(self, send_pkts, recv_pkt_id, wait_forever=False):
        send_pkts = [pkt.ljust(PAYLOAD_LEN, ZERO) for pkt in send_pkts]
        attempts = len(send_pkts) * TIMEOUT / DELAY
        while wait_forever or attempts > 0:
            for send_pkt in send_pkts:
                self.tx.send_pkt(send_pkt)
                # look for received packet
                recv_pkt = self.rx.recv_pkt()
                if recv_pkt:
                    pkt_id = ord(recv_pkt[0])
                    if pkt_id == recv_pkt_id:
                        return recv_pkt
                    self.logger.debug('Received unanticipated packet: 0x%s', pkt_id)
                sleep(DELAY)
                attempts -= 1

    def _send_until_pkt_backoff(self, send_pkts, recv_pkt_id, wait_forever=False):
        send_pkts = [pkt.ljust(PAYLOAD_LEN, ZERO) for pkt in send_pkts]
        attempts = len(send_pkts) * TIMEOUT / DELAY
        while wait_forever or attempts > 0:
            for send_pkt in send_pkts:
                self.tx.send_pkt(send_pkt)
                self.tx.send_pkt(send_pkt)
                self.tx.send_pkt(send_pkt)
                for i in BACKOFF:
                    # look for received packet
                    recv_pkt = self.rx.recv_pkt()
                    if recv_pkt:
                        pkt_id = ord(recv_pkt[0])
                        if pkt_id == recv_pkt_id:
                            return recv_pkt
                        self.logger.debug('Received unanticipated packet: 0x%s', pkt_id)
                    sleep(DELAY)
                attempts -= 1

    def wait_until_pkt(self, recv_pkt_id, wait_forever=False):
        attempts = TIMEOUT / DELAY
        while wait_forever or attempts > 0:
            recv_pkt = self.rx.recv_pkt()
            if recv_pkt:
                pkt_id = ord(recv_pkt[0])
                if pkt_id == recv_pkt_id:
                    return recv_pkt
                self.logger.debug('Received unanticipated packet: 0x%s', pkt_id)
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
            rdhpart11_pkt[:64] +
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
        self.logger.debug('Valid HMAC in HELLO packet')
        # verify hash chain components
        if not self.mac.verifyHash(rh2, rh3):
            self.logger.error('Hash chain verification failed: sha256(h2) != h3')
            return False
        self.logger.debug('Hash chain verification success: sha256(h2) == h3')

        dhpart2_pkts = self.pkt_factory.gen_pkts_dhpart2()
        # prepare dhpart2 packets
        self.logger.debug('Sending packets for DH-part2')
        rconfirm1_pkt = self.send_until_pkt(dhpart2_pkts, PKT_CONFIRM1)
        if not rconfirm1_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_CONFIRM1')
        # dissect fields
        (   rconfirm_mac,
            rh0_enc
        ) = self.pkt_factory.dct_pkt_confirm1(rconfirm1_pkt)

        # set parameters
        self.mac.setPartnerPublicKey(pvr)
        self.mac.setPackets(
            rhello_pkt[:53] +
            icommit_pkt +
            rdhpart11_pkt[:64] +
            rdhpart12_pkt[:64] +
            rdhpart13_pkt[:64] +
            rdhpart14_pkt[:64] +
            rdhpart15_pkt[:61] +
            ''.join(dhpart2_pkts)
        )
        self.mac.computeSecret(self.cache.getZID(), rzid)
        # determine keys
        self.mac.startEncryption(
            self.mac.hmac_s0('Initiator ZRTP key'),
            self.mac.hmac_s0('Responder ZRTP key')
        )

        # verify confirm1 packet
        rconfirmmackey = self.mac.hmac_s0('Responder HMAC key')
        if not self.mac.verifyPacketHMAC(rconfirmmackey, rh0_enc, rconfirm_mac):
            self.logger.error('HMAC failed in responders CONFIRM1 packet')
            return False
        self.logger.debug('Valid HMAC in CONFIRM1 packet')
        # decrypt rh0
        rh0 = self.mac.decrypt(rh0_enc)
        # verify DHPART1 packet mac
        if not self.mac.verifyHash(rh0, rh1):
            self.logger.error('Hash chain verification failed: sha256(h0) != h1')
            return False
        self.logger.debug('Hash chain verification success: sha256(h0) == h1')

        # prepare dhconfirm2 packet
        iconfirm2_pkt = self.pkt_factory.gen_pkt_confirm2()
        self.logger.debug('Sending packets for CONFIRM2')
        self.send(iconfirm2_pkt, 10)

        return True

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
        self.logger.debug('Valid HMAC in HELLO packet')
        # verify hash chain components
        if not self.mac.verifyHash(ih2, ih3):
            self.logger.error('Hash chain verification failed: sha256(h2) != h3')
            return False
        self.logger.debug('Hash chain verification success: sha256(h2) == h3')
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
            idhpart21_pkt[:64] +
            idhpart22_pkt[1:64] +
            idhpart23_pkt[1:64] +
            idhpart24_pkt[1:64] +
            idhpart25_pkt[1:61]
        )
        # verify COMMIT packet
        if not self.mac.verifyPacketHMAC(ih1, icommit_pkt[:53], icommithmac):
            self.logger.error('HMAC failed in initiators COMMIT packet')
            return False
        self.logger.debug('Valid HMAC in COMMIT packet')
        # verify hash chain components
        if not self.mac.verifyHash(ih1, ih2):
            self.logger.error('Hash chain verification failed: sha256(h1) != h2')
            return False
        self.logger.debug('Hash chain verification success: sha256(h1) == h2')

        # set parameters
        self.mac.setPartnerPublicKey(pvi)
        self.mac.setPackets(
            rhello_pkt +
            icommit_pkt[:61] +
            ''.join(dhpart1_pkts) +
            idhpart21_pkt[:64] +
            idhpart22_pkt[:64] +
            idhpart23_pkt[:64] +
            idhpart24_pkt[:64] +
            idhpart25_pkt[:61]
        )
        self.mac.computeSecret(izid, self.cache.getZID())
        # determine keys
        self.mac.startEncryption(
            self.mac.hmac_s0('Responder ZRTP key'),
            self.mac.hmac_s0('Initiator ZRTP key')
        )

        # wait for confirm2
        rconfirm1_pkt = self.pkt_factory.gen_pkt_confirm1()
        self.logger.debug('Sending packet: PKT_CONFIRM1')
        iconfirm2_pkt = self.send_until_pkt([rconfirm1_pkt], PKT_CONFIRM2)
        if not iconfirm2_pkt:
            self.logger.warning('Timeout reached')
            return False
        self.logger.debug('Received packet: PKT_CONFIRM2')
        # dissect fields
        (   iconfirm_mac,
            ih0_enc
        ) = self.pkt_factory.dct_pkt_confirm1(iconfirm2_pkt)

        # verify confirm2 packet
        iconfirmmackey = self.mac.hmac_s0('Initiator HMAC key')
        if not self.mac.verifyPacketHMAC(iconfirmmackey, ih0_enc, iconfirm_mac):
            self.logger.error('HMAC failed in initiators CONFIRM2 packet')
            return False
        self.logger.debug('Valid HMAC in CONFIRM2 packet')
        # decrypt ih0
        ih0 = self.mac.decrypt(ih0_enc)
        # verify DHPART2 packet mac
        if not self.mac.verifyHash(ih0, ih1):
            self.logger.error('Hash chain verification failed: sha256(h0) != h1')
            return False
        self.logger.debug('Hash chain verification success: sha256(h0) == h1')

        return True

    def relayAudio(self):
        with Codec2Source(self.conf.micdev) as voice_src:
            with Codec2Sink(self.conf.outdev) as voice_sink:
                src_samples = ''
                for c2sample in voice_src.read():
                    # send mic input
                    if c2sample:
                        src_samples += c2sample
                        if len(src_samples) >= 63:
                            self.send(self.pkt_factory.gen_pkt_codec2(src_samples[:63]), 2)
                            src_samples = src_samples[63:]
                    # check for received audio
                    recv_pkt = self.rx.recv_pkt()
                    if recv_pkt and recv_pkt[0] == PKT_CODEC2_CHR:
                        try:
                            c2data = self.pkt_factory.dct_pkt_codec2(recv_pkt)
                            voice_sink.write(c2data)
                        except InvalidHMACException:
                            self.logger.error('Bad HMAC in codec2 data packet')
                    #else:
                    #    print 'writing silence...'
                    #    voice_sink.write_silence()

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
            self.conf.lomicdev,
            self.conf.listen
        )

        self.rx.start()
        self.tx.start()

        if self.conf.initiate:
            # initiate communication
            proceed = self._initiate()
        else:
            proceed = self._respond()

        if proceed:
            self.logger.info('Authentication successful, starting voice relay...')
            self.relayAudio()

        self.tx.stop()
        self.rx.stop()
