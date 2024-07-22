import subprocess
import time
import mmwave as mm
from mmwave.dataloader import DCA1000
import numpy as np
import mmwave.dsp as dsp
import mmwave.clustering as clu
import matplotlib.pyplot as plt
from dashboard import RadarDashboard
import threading
import time
from queue import Queue, Empty
import numpy as np
import matplotlib.pyplot as plt
from plotting import *
from mmwave.dsp.utils import Window
import os

numFrames = 0
numADCSamples = 256
numTxAntennas = 2
numRxAntennas = 4
numLoopsPerFrame = 128
numChirpsPerFrame = numTxAntennas * numLoopsPerFrame #256
#numChirpsPerFrame = 128
numRangeBins = numADCSamples
numDopplerBins = numLoopsPerFrame
numAngleBins = 64
sampleRate = 10000
range_resolution, bandwidth = dsp.range_resolution(numADCSamples, sampleRate)
doppler_resolution = dsp.doppler_resolution(bandwidth)

dB_threshold = 80
targetDistance = 5
rangeBinThreshold = int(targetDistance / range_resolution)
rangeBinThreshold = min(rangeBinThreshold, numRangeBins)


def write_to_file(filename, data):
    with open(filename, 'a') as f:
        f.write(data + '\n')

def detect_hand(processed_frame, range_axis, min_range=0.35, max_range=1, threshold_db=125):
    valid_range_indices = np.where((range_axis >= min_range) & (range_axis <= max_range))[0]
    
    hand_detected = np.any(processed_frame[valid_range_indices] > threshold_db)
    
    if hand_detected:
        max_value_index = np.argmax(processed_frame[valid_range_indices])
        detected_distance = range_axis[valid_range_indices[max_value_index]]
    else:
        detected_distance = None
    
    return hand_detected, detected_distance

def process_frame(frame):
    magnitudes = np.abs(frame[0][0])
    magnitudes_db = 20 * np.log10(magnitudes)
    return magnitudes_db

def process_range_fft(frame):
    range_resolution = 0.1954
    num_range_bins = numADCSamples 
    max_range = range_resolution * num_range_bins
    radar_cube = dsp.range_processing(frame, window_type_1d=Window.HANNING)
    magnitude_db = 20 * np.log10(np.abs(radar_cube[0][0]))
    range_axis = np.linspace(0, max_range, num_range_bins)
    return range_axis, magnitude_db, radar_cube

def main():
    cmd_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime\RunCustomScripts.cmd'
    studio_runtime_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime'

    subprocess.Popen(cmd_path, cwd=studio_runtime_path)
    print("Starting mmWave Studio...")
    time.sleep(110)
    print("mmWave Studio should be ready now.")

    dca = DCA1000()
    print("DCA1000 initialized.")

    data_queue = Queue()

    dashboard = RadarDashboard()
    dashboard_thread = threading.Thread(target=dashboard.run, daemon=True)
    dashboard_thread.start()
    print("Dashboard thread started.")
    dashboard.update_status("Dashboard initialised.")

    def update_dashboard():
        while True:
            try:
                data = data_queue.get(timeout=1)
                if data is None:
                    break 
                frame, status = data
                if status is not None:
                    dashboard.update_status(status)
                if frame is not None:
                    real_data = frame[0][0].real
                    imag_data = frame[0][0].imag
                    dashboard.update_plot("plot-0", (real_data, imag_data), "scatter", "Raw ADC Data (I/Q)")
                    
                    processed_frame = process_frame(frame)
                    dashboard.update_plot("plot-1", processed_frame, "scatter", "Processed Frame Data")

                    range_axis, processed_frame_range_fft, radar_cube = process_range_fft(frame)
                    dashboard.update_plot("plot-2", (range_axis, processed_frame_range_fft), "scatter", "Range FFT Frame Data")

                    hand_detected, detected_distance = detect_hand(processed_frame_range_fft, range_axis, min_range=0.35, max_range=1)
                    if hand_detected:
                        hand_status = f"Yes (Distance: {detected_distance:.2f}m)"
                    else:
                        hand_status = "No"
                    dashboard.update_status(f"Hand above sensor: {hand_status}")

            except Empty:
                continue

    update_thread = threading.Thread(target=update_dashboard, daemon=True)
    update_thread.start()
    print("Dashboard update thread started.")

    try:
        output_file = 'radar_output.txt'
        open(output_file, 'w').close()

        raw_frame = dca.read()
        write_to_file(output_file, f"Size frame RAW: {raw_frame.shape}")
        write_to_file(output_file, f"Type frame RAW: {raw_frame.dtype}")
        write_to_file(output_file, f"First sample of first chirp RAW: {raw_frame}")
        write_to_file(output_file, f"First sample of first chirp RAW: {raw_frame[0]}")


        frame = dca.organize(raw_frame, num_chirps=numChirpsPerFrame, num_rx=numRxAntennas, num_samples=numADCSamples)
        write_to_file(output_file, f"Size frame: {frame.shape}")
        write_to_file(output_file, f"Type frame RAW: {frame.dtype}")
        write_to_file(output_file, f"First sample of first chirp: {frame[0][0]}")
        write_to_file(output_file, f"Full frame: {frame}")
        write_to_file(output_file, f"First chirp: {frame[0]}")

        while True:
            raw_frame = dca.read()
            frame = dca.organize(raw_frame, num_chirps=numChirpsPerFrame, num_rx=numRxAntennas, num_samples=numADCSamples)
            data_queue.put((frame, "Reading raw data..."))

    except KeyboardInterrupt:
        print("Stopping the program...")
        return
    except Exception as e:
        write_to_file(output_file, f"An error occurred: {str(e)}")

    finally:
        data_queue.put((None, None))
        update_thread.join()
        dashboard_thread.join()
        print("Program stopped.")

if __name__ == "__main__":
    main()
