#!/usr/bin/env python
'''
Stores stateful cryptographic routines
'''

from os.path import expanduser, isfile
from pickle import load as pickleLoad, dump as pickleDump

from Crypto import Random
from Crypto.Hash import SHA256

VOIZ_CACHE_PATH = expanduser('~/.voiz_cache')

class VoiZCache():

    def __init__(self, path=VOIZ_CACHE_PATH):
        self.path = path
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
        with open(self.path, 'wb') as fp:
            pickleDump(self.cache, fp)

    def getZID(self):
        return self.cache['ZID']

class VoiZMAC():

    def __init__(self):
        self.prng = Random.new()

    def _computeHashChain(self):
        self.h0 = self.prng.read(32)
        self.h1 = SHA256.new(self.h0).digest()
        self.h2 = SHA256.new(self.h1).digest()
        self.h3 = SHA256.new(self.h2).digest()