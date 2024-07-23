import subprocess
import time
import threading
from queue import Queue, Empty
import numpy as np
import matplotlib.pyplot as plt
import yaml
#from mmwave.dataloader import DCA1000
from data_fetching import DCA1000
import mmwave.dsp as dsp
from mmwave.dsp.utils import Window
from dashboard import RadarDashboard
from data_handling import RadarProcessor

def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

CONFIG = load_config()



class RadarSystem:
    def __init__(self, config):
        self.config = config
        self.processor = RadarProcessor(config)
        self.dca = DCA1000(config, config['dca1000']['static_ip'], config['dca1000']['adc_ip'], config['dca1000']['data_port'], config['dca1000']['config_port'])
        #self.dca = DCA1000(config['dca1000']['static_ip'], config['dca1000']['adc_ip'], config['dca1000']['data_port'], config['dca1000']['config_port'])
        self.dashboard = RadarDashboard()
        self.data_queue = Queue()

    def write_to_file(self, data):
        with open(self.config['paths']['output_file'], 'a') as f:
            f.write(data + '\n')

    def start_mmwave_studio(self):
        subprocess.Popen(self.config['paths']['cmd_path'], cwd=self.config['paths']['studio_runtime_path'])
        self.write_to_file("Starting mmWave Studio...")
        time.sleep(170)
        self.write_to_file("mmWave Studio should be ready now.")

    def update_dashboard(self):
        while True:
            try:
                data = self.data_queue.get(timeout=1)
                if data is None:
                    break 
                frame, status = data
                if status is not None:
                    self.dashboard.update_status(status)
                if frame is not None:
                    self.process_and_update_plots(frame)
            except Empty:
                continue

    def process_and_update_plots(self, frame):
        #fixed_frame = frame - (frame >= 2**15) * 2**16
        real_data, imag_data = frame[0][0].real, frame[0][0].imag
        
        self.dashboard.update_plot("plot-0", (real_data, imag_data), "scatter", "Raw ADC Data (I/Q)")
        
        processed_frame = self.processor.process_frame(frame)
        self.dashboard.update_plot("plot-1", processed_frame, "scatter", "Processed Frame Data")

        range_axis, processed_frame_range_fft, _ = self.processor.process_range_fft(frame)
        self.dashboard.update_plot("plot-2", (range_axis, processed_frame_range_fft), "scatter", "Range FFT Frame Data")

        hand_detected, detected_distance = self.processor.detect_hand(processed_frame_range_fft, range_axis)
        hand_status = f"Yes (Distance: {detected_distance:.2f}m)" if hand_detected else "No"
        self.dashboard.update_status(f"Hand above sensor: {hand_status}")

    def run(self):
        self.start_mmwave_studio()
        self.write_to_file("DCA1000 initialized.")

        dashboard_thread = threading.Thread(target=self.dashboard.run, daemon=True)
        dashboard_thread.start()
        self.dashboard.update_status("Dashboard initialised.")
        self.write_to_file("Dashboard thread started.")

        update_thread = threading.Thread(target=self.update_dashboard, daemon=True)
        update_thread.start()
        self.write_to_file("Dashboard update thread started.")

        try:
            self.process_frames()
        except KeyboardInterrupt:
            print("Stopping the program...")
        except Exception as e:
            self.write_to_file(f"An error occurred: {str(e)}")
        finally:
            self.data_queue.put((None, None))
            update_thread.join()
            dashboard_thread.join()
            print("Program stopped.")

    def process_frames(self):
        self.write_to_file(f"Before DCA READ")
        raw_frame = self.dca.read()
        self.write_to_file(f"AFTER DCA READ")

        self.write_to_file(f"Frame RAW: {raw_frame}")
        self.write_to_file(f"Size frame RAW: {raw_frame.shape}")
        self.write_to_file(f"Type frame RAW: {raw_frame.dtype}")
        self.write_to_file(f"Before DCA organize")

        frame = self.dca.organize(raw_frame, num_chirps=self.processor.num_chirps_per_frame, 
                                  num_rx=self.config['radar']['num_rx_antennas'], 
                                  num_samples=self.config['radar']['num_adc_samples'])
        self.write_to_file(f"After DCA organize")
        self.write_to_file(f"Size frame: {frame.shape}")
        self.write_to_file(f"Type frame RAW: {frame.dtype}")
    
        while True:
            raw_frame = self.dca.read()
            frame = self.dca.organize(raw_frame, num_chirps=self.processor.num_chirps_per_frame, 
                                      num_rx=self.config['radar']['num_rx_antennas'], 
                                      num_samples=self.config['radar']['num_adc_samples'])
            self.data_queue.put((frame, "Reading raw data..."))

def main():
    config = load_config()
    radar_system = RadarSystem(config)
    radar_system.run()

if __name__ == "__main__":
    main()

