#!/usr/bin/env python

from os import O_NONBLOCK
from fcntl import fcntl, F_GETFL, F_SETFL
from subprocess import Popen, PIPE
from logging import getLogger

import alsaaudio

CODEC2ENC_PATH = '/home/j/codec2/build_linux/src/c2enc'
CODEC2DEC_PATH = '/home/j/codec2/build_linux/src/c2dec'
CODEC2_MODE = 1400   # can be any of 3200|2400|1600|1400|1300|1200

class Codec2Source():

    def __init__(self, micdev):
        self.logger = getLogger('codec2-src')
        self.logger.debug('Using device `%s` as mic source', micdev)
        self.micdev = micdev

    def __enter__(self):
        self.inp = alsaaudio.PCM(
            alsaaudio.PCM_CAPTURE,
            alsaaudio.PCM_NORMAL,
            self.micdev
        )
        self.inp.setchannels(1)
        self.inp.setrate(8000)
        self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self.inp.setperiodsize(160)

        c2args = (CODEC2ENC_PATH, str(CODEC2_MODE), '-', '-')
        self.proc = Popen(c2args, stdin=PIPE, stdout=PIPE)

        # set stdout to nonblocking
        fd = self.proc.stdout.fileno()
        fl = fcntl(fd, F_GETFL)
        fcntl(fd, F_SETFL, fl | O_NONBLOCK)

        return self

    def __exit__(self, type, value, traceback):
        self.proc.stdin.close()
        self.inp.close()

    def read(self):
        inp_read = self.inp.read
        proc_read = self.proc.stdout.read
        proc_write = self.proc.stdin.write
        while True:
            num_frames, micdata = inp_read()
            if num_frames > 0:
                proc_write(micdata)
            try:
                yield proc_read()
            except IOError:
                yield None

class Codec2Sink():

    def __init__(self, outdev):
        self.logger = getLogger('codec2-sink')
        self.logger.debug('Using device `%s` as out sink', outdev)
        self.outdev = outdev

    def __enter__(self):
        self.out = alsaaudio.PCM(
            alsaaudio.PCM_PLAYBACK,
            alsaaudio.PCM_NORMAL,
            self.outdev
        )
        self.out.setchannels(1)
        self.out.setrate(8000)
        self.out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self.out.setperiodsize(160)

        c2args = (CODEC2DEC_PATH, str(CODEC2_MODE), '-', '-')
        self.proc = Popen(c2args, stdin=PIPE, stdout=PIPE)

        # set stdout to nonblocking
        fd = self.proc.stdout.fileno()
        fl = fcntl(fd, F_GETFL)
        fcntl(fd, F_SETFL, fl | O_NONBLOCK)

        return self

    def __exit__(self, type, value, traceback):
        self.proc.stdin.close()
        self.out.close()

    def write(self, c2data):
        self.proc.stdin.write(c2data)
        try:
            self.out.write(self.proc.stdout.read())
        except IOError:
            pass