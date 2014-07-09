#!/usr/bin/env python
'''
Stores stateful cryptographic routines
'''

from os.path import expanduser, isfile
from pickle import load as pickleLoad, dump as pickleDump
from logging import getLogger

from Crypto import Random
from Crypto.Hash import SHA256, HMAC

VOIZ_CACHE_PATH = '~/.voiz_cache'

class VoiZCache():

    def __init__(self, path=VOIZ_CACHE_PATH):
        self.logger = getLogger('cache')
        self.path = expanduser(path)
        self.logger.debug('Using VoiZ cache file `%s`' % self.path)
        self.load()

    def newZID(self):
        return Random.new().read(12)

    def load(self):
        if not isfile(self.path):
            self.cache = {
                'ZID':  self.newZID()
            }
            self.save()
            return
        with open(self.path, 'rb') as fp:
            self.cache = pickleLoad(fp)

    def save(self):
        with open(self.path, 'rb') as fp:
            pickleDump(self.cache, fp)

class VoiZMAC():

    def __init__(self):
        self.logger = getLogger('mac')
        self.prng = Random.new()
        self._computeHashChain()

    def _computeHashChain(self):
        self.logger.debug('Generating MAC hash chain...')
        self.h0 = self.prng.read(32)
        self.h1 = SHA256.new(self.h0).digest()
        self.h2 = SHA256.new(self.h1).digest()
        self.h3 = SHA256.new(self.h2).digest()

    def hmac_h2(self, payload):
        return HMAC.new(self.h2, payload, SHA256).digest()
