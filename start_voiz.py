#!/usr/bin/env python

__author__ = 'Julian Melchert <jpm28@students.waikato.ac.nz>'
__version__ = '1.0.1'
__status__ = 'prototype'

import logging
from argparse import ArgumentParser

from voiz.app import VoiZApp

LOG_FMT         = '%(asctime)s %(name)-15s %(levelname)-7s %(message)s'
LOG_DATEFMT     = '%y-%m-%d %H:%M:%S'

def setupLogging(consolelevel=logging.INFO):
    logging.basicConfig(
        level   = consolelevel,
        format  = LOG_FMT,
        datefmt = LOG_DATEFMT
    )

def loadConfig():
    parser = ArgumentParser()
    parser.add_argument(
        '-micdev',
        type=str,
        help='ALSA card/device to use as voice capture',
        default='plughw:0,0'
    )
    parser.add_argument(
        '-outdev',
        type=str,
        help='ALSA card/device to use for voice playback',
        default='plughw:0,0'
    )
    parser.add_argument(
        '-lomicdev',
        type=str,
        help='ALSA card/device to use for loopback capture',
        default='plughw:1,1'
    )
    parser.add_argument(
        '-looutdev',
        type=str,
        help='ALSA card/device to use for loopback playback',
        default='plughw:1,1'
    )
    parser.add_argument(
        '-carrier',
        type=int,
        help='carrier frequency for digital GFSK',
        default=2400
    )
    parser.add_argument(
        '-sideband',
        type=int,
        help='sideband frequency for digital GFSK',
        default=2300
    )
    parser.add_argument(
        '-transition',
        type=int,
        help='transition frequency for digital GFSK',
        default=240
    )
    parser.add_argument(
        '-sps',
        type=int,
        help='samples/symbol for digital GFSK',
        default=2
    )
    parser.add_argument(
        '-interpolation',
        type=int,
        help='interpolation/decimation for resampler',
        default=8
    )
    parser.add_argument(
        '--verbose',
        help='print more information',
        action='store_true'
    )
    parser.add_argument(
        '--initiate',
        help='act as the initiator',
        action='store_true'
    )
    parser.add_argument(
        '--listen',
        help='[debug] listen to received audio (uses dev hw:0,0)',
        action='store_true'
    )
    parser.add_argument(
        '--backoff',
        help='wait between transmissions',
        action='store_true'
    )
    return parser.parse_args()

if __name__ == '__main__':
    # load run configuration
    conf = loadConfig()

    setupLogging(logging.DEBUG if conf.verbose else logging.INFO)

    logging.info('Starting VoiZ')
    voiz = VoiZApp(conf)
    try:
        voiz.run()
    except KeyboardInterrupt:
        pass

    logging.info('Exiting cleanly')
