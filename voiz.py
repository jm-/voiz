#! /usr/bin/env python

__author__ = 'Julian Melchert <jpm28@students.waikato.ac.nz>'
__version__ = '1.0.1'
__status__ = 'prototype'

import logging
from argparse import ArgumentParser

LOG_FMT         = '%(asctime)s %(name)-15s %(levelname)-7s %(message)s'
LOG_DATEFMT     = '%y-%m-%d %H:%M:%S'

def setupLogging(consolelevel=logging.DEBUG):
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
        default='default'
    )
    parser.add_argument(
        '-speakerdev',
        type=str,
        help='ALSA card/device to use for voice playback',
        default='default'
    )
    return parser.parse_args()

if __name__ == '__main__':
    setupLogging()

    # load run configuration
    logging.debug('Loading configuration')
    conf = loadConfig()



    logging.info('Exiting cleanly')