#!/usr/bin/env python

from gnuradio import audio
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2

class tx_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Transmit block")

        ##################################################
        # Variables
        ##################################################
        self.transistion = transistion = 250
        self.sps = sps = 2
        self.sideband = sideband = 2300
        self.samp_rate = samp_rate = 48000
        self.payloadlen = payloadlen = 25
        self.interpolation = interpolation = 8
        self.carrier_tx = carrier_tx = 2400

        ##################################################
        # Blocks
        ##################################################
        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=interpolation,
                decimation=1,
                taps=None,
                fractional_bw=None,
        )
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(1, (firdes.band_pass (0.50,samp_rate,carrier_tx-sideband,carrier_tx+sideband,transistion)), -carrier_tx, samp_rate)
        self.digital_gfsk_mod_0 = digital.gfsk_mod(
            samples_per_symbol=sps,
            sensitivity=1.0,
            bt=0.35,
            verbose=False,
            log=False,
        )
        self.blocks_complex_to_real_0 = blocks.complex_to_real(1)
        self.blks2_packet_encoder_0 = grc_blks2.packet_mod_b(grc_blks2.packet_encoder(
                samples_per_symbol=sps,
                bits_per_symbol=1,
                preamble="",
                access_code="",
                pad_for_usrp=False,
            ),
            payload_length=payloadlen,
        )
        self.audio_sink_0 = audio.sink(samp_rate, "plughw:1,1,0", True)

        self.source_queue = gr.msg_queue()
        self.msg_source = blocks.message_source(gr.sizeof_char, self.source_queue)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.msg_source, 0), (self.blks2_packet_encoder_0, 0))
        self.connect((self.blks2_packet_encoder_0, 0), (self.digital_gfsk_mod_0, 0))
        self.connect((self.digital_gfsk_mod_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.blocks_complex_to_real_0, 0))
        self.connect((self.blocks_complex_to_real_0, 0), (self.audio_sink_0, 0))

    def send_pkt(self, payload):
        self.source_queue.insert_tail(gr.message_from_string(payload))