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


numFrames = 0
numADCSamples = 256
numTxAntennas = 3
numRxAntennas = 4
numLoopsPerFrame = 128
numChirpsPerFrame = numTxAntennas * numLoopsPerFrame
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

plotRangeDopp = True  
plot2DscatterXY = True  
plot2DscatterXZ = False  
plot3Dscatter = False  
plotCustomPlt = False



def process_data(radar_plot, frame, numRangeBins, range_resolution):
    # Range
    print(frame)
    radar_cube = dsp.range_processing(frame, window_type_1d=Window.BLACKMAN)
    assert radar_cube.shape == (
    numChirpsPerFrame, numRxAntennas, numADCSamples), "[ERROR] Radar cube is not the correct shape!"

    # Doppler 
    det_matrix, aoa_input = dsp.doppler_processing(radar_cube, num_tx_antennas=numTxAntennas, clutter_removal_enabled=True)

    # Object Detection
    fft2d_sum = det_matrix.astype(np.int64)
    thresholdDoppler, noiseFloorDoppler = np.apply_along_axis(func1d=dsp.ca_,
                                                                axis=0,
                                                                arr=fft2d_sum.T,
                                                                l_bound=1.5,
                                                                guard_len=4,
                                                                noise_len=16)

    thresholdRange, noiseFloorRange = np.apply_along_axis(func1d=dsp.ca_,
                                                            axis=0,
                                                            arr=fft2d_sum,
                                                            l_bound=2.5,
                                                            guard_len=4,
                                                            noise_len=16)

    thresholdDoppler, noiseFloorDoppler = thresholdDoppler.T, noiseFloorDoppler.T
    det_doppler_mask = (det_matrix > thresholdDoppler)
    det_range_mask = (det_matrix > thresholdRange)

    # Indices of peaks
    full_mask = (det_doppler_mask & det_range_mask)
    det_peaks_indices = np.argwhere(full_mask == True)

    # peakVals and SNR 
    peakVals = fft2d_sum[det_peaks_indices[:, 0], det_peaks_indices[:, 1]]
    snr = peakVals - noiseFloorRange[det_peaks_indices[:, 0], det_peaks_indices[:, 1]]

    dtype_location = '(' + str(numTxAntennas) + ',)<f4'
    dtype_detObj2D = np.dtype({'names': ['rangeIdx', 'dopplerIdx', 'peakVal', 'location', 'SNR'],
                                'formats': ['<i4', '<i4', '<f4', dtype_location, '<f4']})
    detObj2DRaw = np.zeros((det_peaks_indices.shape[0],), dtype=dtype_detObj2D)
    detObj2DRaw['rangeIdx'] = det_peaks_indices[:, 0].squeeze()
    detObj2DRaw['dopplerIdx'] = det_peaks_indices[:, 1].squeeze()
    detObj2DRaw['peakVal'] = peakVals.flatten()
    detObj2DRaw['SNR'] = snr.flatten()

    detObj2DRaw = dsp.prune_to_peaks(detObj2DRaw, det_matrix, numDopplerBins, reserve_neighbor=True)

    detObj2D = dsp.peak_grouping_along_doppler(detObj2DRaw, det_matrix, numDopplerBins)
    SNRThresholds2 = np.array([[2, 23], [10, 11.5], [35, 16.0]])
    peakValThresholds2 = np.array([[4, 275], [1, 400], [500, 0]])
    detObj2D = dsp.range_based_pruning(detObj2D, SNRThresholds2, peakValThresholds2, numRangeBins, 0.5, range_resolution)

    print(detObj2D.shape)
    azimuthInput = aoa_input[detObj2D['rangeIdx'], :, detObj2D['dopplerIdx']]

    x, y, z = dsp.naive_xyz(azimuthInput.T, num_tx=numTxAntennas, num_rx=numRxAntennas)
    xyzVecN = np.zeros((3, x.shape[0]))
    xyzVecN[0] = x * range_resolution * detObj2D['rangeIdx']
    xyzVecN[1] = y * range_resolution * detObj2D['rangeIdx']
    xyzVecN[2] = z * range_resolution * detObj2D['rangeIdx']

    Psi, Theta, Ranges, xyzVec = dsp.beamforming_naive_mixed_xyz(azimuthInput, detObj2D['rangeIdx'],
                                                                    range_resolution, method='Capon', num_vrx=12)

    # 3D-Clustering
    numDetObjs = detObj2D.shape[0]
    print(numDetObjs)
    dtf = np.dtype({'names': ['rangeIdx', 'dopplerIdx', 'peakVal', 'location', 'SNR'],
                    'formats': ['<f4', '<f4', '<f4', dtype_location, '<f4']})
    detObj2D_f = detObj2D.astype(dtf)
    detObj2D_f = detObj2D_f.view(np.float32).reshape(-1, 7)

    for i, currRange in enumerate(Ranges):
        if i >= (detObj2D_f.shape[0]):
            detObj2D_f = np.insert(detObj2D_f, i, detObj2D_f[i - 1], axis=0)
        if currRange == detObj2D_f[i][0]:
            detObj2D_f[i][3] = xyzVec[0][i]
            detObj2D_f[i][4] = xyzVec[1][i]
            detObj2D_f[i][5] = xyzVec[2][i]
        else:  
            detObj2D_f = np.insert(detObj2D_f, i, detObj2D_f[i - 1], axis=0)
            detObj2D_f[i][3] = xyzVec[0][i]
            detObj2D_f[i][4] = xyzVec[1][i]
            detObj2D_f[i][5] = xyzVec[2][i]

    cluster = clu.radar_dbscan(detObj2D_f, 0, doppler_resolution, use_elevation=True)

    cluster_np = np.array(cluster['size']).flatten()
    if cluster_np.size != 0:
        if max(cluster_np) > max_size:
            max_size = max(cluster_np)

    if plot2DscatterXY or plot2DscatterXZ:

        if plot2DscatterXY:
            xyzVec = xyzVec[:, (np.abs(xyzVec[2]) < 1.5)]
            xyzVecN = xyzVecN[:, (np.abs(xyzVecN[2]) < 1.5)]
            axes[0].set_ylim(bottom=0, top=10)
            axes[0].set_ylabel('Range')
            axes[0].set_xlim(left=-4, right=4)
            axes[0].set_xlabel('Azimuth')
            axes[0].grid(b=True)

            axes[1].set_ylim(bottom=0, top=10)
            axes[1].set_xlim(left=-4, right=4)
            axes[1].set_xlabel('Azimuth')
            axes[1].grid(b=True)

        elif plot2DscatterXZ:
            axes[0].set_ylim(bottom=-5, top=5)
            axes[0].set_ylabel('Elevation')
            axes[0].set_xlim(left=-4, right=4)
            axes[0].set_xlabel('Azimuth')
            axes[0].grid(b=True)


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
                dashboard.update_status(status)
                #print(frame)
                if frame is not None:

                    dashboard.update_plot("plot-0", frame[0][0].real, "scatter")
                    
                    # Example of adding a processed data plot
                    # processed_data = process_frame(frame)
                    # dashboard.update_plot("plot-1", processed_data, "scatter")
            except Empty:
                continue 

    update_thread = threading.Thread(target=update_dashboard, daemon=True)
    update_thread.start()
    print("Dashboard update thread started.")


    try:
        time.sleep(10)
        raw_frame = dca.read()
        frame = dca.organize(raw_frame, num_chirps=numChirpsPerFrame, num_rx=numRxAntennas, num_samples=numADCSamples)
        print(frame)
        print(frame[0])
        print(frame[0][0])
        
        while True:
            raw_frame = dca.read()
            frame = dca.organize(raw_frame, num_chirps=numChirpsPerFrame, num_rx=numRxAntennas, num_samples=numADCSamples)
            data_queue.put((frame, "Reading raw data..."))

    except KeyboardInterrupt:
        print("Stopping the program...")
        return

    finally:
        data_queue.put((None, None))
        update_thread.join()
        dashboard_thread.join()
        print("Program stopped.")

if __name__ == "__main__":
    main()

#process_data(None, frame, numRangeBins, range_resolution)