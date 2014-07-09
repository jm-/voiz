#!/usr/bin/env python

from logging import getLogger

from .tx import tx_block
from .rx import rx_block
from .crypto import VoiZCache

class VoiZApp():

    def __init__(self, conf):
        self.logger = getLogger('VoiZ-app')
        self.conf = conf
        self.cache = VoiZCache()
        self.logger.info('Using ZID = 0x%s', self.cache.getZID().encode('hex'))

    def _initiate(self):
        pass

    def _respond(self):
        pass

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
            self.conf.looutdev
        )

        self.rx.start()
        self.tx.start()

        if self.conf.initiate:
            # initiate communication
            self._initiate()
        else:
            self._respond()

            self.tx.stop()
            self.rx.stop()