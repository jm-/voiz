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

DH_MODULUS = int('''
    FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
    29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
    EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
    E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
    EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE45B3D
    C2007CB8 A163BF05 98DA4836 1C55D39A 69163FA8 FD24CF5F
    83655D23 DCA3AD96 1C62F356 208552BB 9ED52907 7096966D
    670C354E 4ABC9804 F1746C08 CA18217C 32905E46 2E36CE3B
    E39E772C 180E8603 9B2783A2 EC07A28F B5C55DF0 6F4C52C9
    DE2BCBF6 95581718 3995497C EA956AE5 15D22618 98FA0510
    15728E5A 8AACAA68 FFFFFFFF FFFFFFFF
'''.replace(' ', '').replace('\n', '').lower(), 16)
DH_GENERATOR = 2

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
        with open(self.path, 'wb') as fp:
            pickleDump(self.cache, fp)

    def getZID(self):
        return self.cache['ZID']

class VoiZMAC():

    def __init__(self):
        self.logger = getLogger('mac')
        self.prng = Random.new()
        self._computeHashChain()
        self._computeDHKeypair()

    def _computeHashChain(self):
        self.logger.debug('Generating MAC hash chain...')
        self.h0 = self.prng.read(32)
        self.h1 = self.getHash(self.h0)
        self.h2 = self.getHash(self.h1)
        self.h3 = self.getHash(self.h2)

    def _computeDHKeypair(self):
        self.logger.debug('Generating Finite Field DH keypair...')
        self.dhpriv = int(self.prng.read(2047).encode('hex'), 16)
        self.dhpub = pow(DH_GENERATOR, self.dhpriv, DH_MODULUS)

    def hmac_h2(self, payload):
        return HMAC.new(self.h2, payload, SHA256).digest()

    def hmac_h1(self, payload):
        return HMAC.new(self.h1, payload, SHA256).digest()

    def hmac_h0(self, payload):
        return HMAC.new(self.h0, payload, SHA256).digest()

    def generateCounterSuffix(self):
        self.counter_suffix = self.prng.read(8)
        return self.counter_suffix

    def setCounterSuffix(self, cs):
        self.counter_suffix = cs

    def packedPublicKey(self):
        return hex(self.dhpub).rstrip('L')[2:].rjust(512, '0').decode('hex')

    def setPartnerPublicKey(self, key):
        self.dhpub2 = int(key.encode('hex'), 16)

    def setPackets(self, packets):
        self.total_hash = self.getHash(packets)

    def computeSecret(self, zidi, zidr):
        dhresult = hex(pow(self.dhpub2, self.dhpriv, DH_MODULUS)).rstrip('L')[2:]
        self.s0 = self.getHash(
            dhresult +
            'ZRTP-HMAC-KDF' +
            zidi +
            zidr +
            self.total_hash
        )

    def verifyPacketHMAC(self, key, payload, expected):
        return HMAC.new(key, payload, SHA256).digest()[:8] == expected

    def verifyHash(self, payload, expected):
        return SHA256.new(payload).digest() == expected

    def getHash(self, payload):
        return SHA256.new(payload).digest()