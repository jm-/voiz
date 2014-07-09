#!/usr/bin/env python

from gnuradio import audio
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2

class top_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Receive block")

        ##################################################
        # Variables
        ##################################################
        self.transition = transition = 250
        self.sps = sps = 2
        self.sideband_rx = sideband_rx = 2300
        self.samp_rate = samp_rate = 48000
        self.interpolation = interpolation = 8
        self.carrier_rx = carrier_rx = 2400

        ##################################################
        # Blocks
        ##################################################
        self.rational_resampler_xxx_0_0_0 = filter.rational_resampler_ccc(
                interpolation=1,
                decimation=interpolation,
                taps=None,
                fractional_bw=None,
        )
        self.freq_xlating_fir_filter_xxx_0_0 = filter.freq_xlating_fir_filter_ccc(1, (firdes.low_pass(1, samp_rate, sideband_rx,transition)), carrier_rx, samp_rate)
        self.digital_gfsk_demod_0 = digital.gfsk_demod(
            samples_per_symbol=sps,
            sensitivity=1.0,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,
            log=False,
        )
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char*1, "/media/salver/University/Honours/conf.example.output", False)
        self.blocks_file_sink_1.set_unbuffered(False)
        self.blks2_packet_decoder_0 = grc_blks2.packet_demod_b(grc_blks2.packet_decoder(
                access_code="",
                threshold=-1,
                callback=lambda ok, payload: self.blks2_packet_decoder_0.recv_pkt(ok, payload),
            ),
        )
        self.audio_source_0 = audio.source(samp_rate, "plughw:1,1,0", True)

        self.fft_filter_xxx_1 = filter.fft_filter_ccc(1, (firdes.complex_band_pass_2(1.0,samp_rate,carrier_rx-sideband_rx,carrier_rx+sideband_rx,transition,100,firdes.WIN_HAMMING,6.76)), 1)
        self.fft_filter_xxx_1.declare_sample_delay(0)

        self.sink_queue = gr.msg_queue()
        self.msg_sink = blocks.message_sink(gr.sizeof_char, self.sink_queue, False)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blks2_packet_decoder_0, 0), (self.msg_sink, 0))
        self.connect((self.blks2_packet_decoder_0, 0), (self.blocks_file_sink_1, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0_0, 0), (self.rational_resampler_xxx_0_0_0, 0))
        self.connect((self.digital_gfsk_demod_0, 0), (self.blks2_packet_decoder_0, 0))
        self.connect((self.audio_source_0, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.fft_filter_xxx_1, 0))
        self.connect((self.fft_filter_xxx_1, 0), (self.freq_xlating_fir_filter_xxx_0_0, 0))
        self.connect((self.rational_resampler_xxx_0_0_0, 0), (self.digital_gfsk_demod_0, 0))

    def recv_pkt(self):
        if self.sink_queue.count() > 0:
            return self.sink_queue.delete_head().to_string()