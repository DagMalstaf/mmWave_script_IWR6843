import numpy as np
import mmwave.dsp as dsp
from mmwave.dsp.utils import Window

class RadarProcessor:
    def __init__(self, config):
        self.config = config
        self.num_chirps_per_frame = config['radar']['num_tx_antennas'] * config['radar']['num_loops_per_frame']
        self.num_range_bins = config['radar']['num_adc_samples']
        self.num_doppler_bins = config['radar']['num_loops_per_frame']
        self.range_resolution, self.bandwidth = dsp.range_resolution(config['radar']['num_adc_samples'], config['radar']['sample_rate'])
        self.doppler_resolution = dsp.doppler_resolution(self.bandwidth)

    def detect_hand(self, processed_frame, range_axis):
        hand_config = self.config['hand_detection']
        valid_range_indices = np.where((range_axis >= hand_config['min_range']) & (range_axis <= hand_config['max_range']))[0]
        hand_detected = np.any(processed_frame[valid_range_indices] > hand_config['threshold_db'])
        
        if hand_detected:
            max_value_index = np.argmax(processed_frame[valid_range_indices])
            detected_distance = range_axis[valid_range_indices[max_value_index]]
        else:
            detected_distance = None
        
        return hand_detected, detected_distance

    def process_frame(self, frame):
        magnitudes = np.abs(frame[0][0])
        return 20 * np.log10(magnitudes)

    def process_range_fft(self, frame):
        max_range = self.config['radar']['range_resolution'] * self.num_range_bins
        radar_cube = dsp.range_processing(frame, window_type_1d=Window.HANNING)
        magnitude_db = 20 * np.log10(np.abs(radar_cube[0][0]))
        range_axis = np.linspace(0, max_range, self.num_range_bins)
        return range_axis, magnitude_db, radar_cube