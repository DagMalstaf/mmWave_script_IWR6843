import subprocess
import time
import mmwave as mm
from mmwave.dataloader import DCA1000
import numpy as np
import mmwave.dsp as dsp
import mmwave.clustering as clu
import matplotlib.pyplot as plt

numFrames = 0
numADCSamples = 256
numTxAntennas = 2
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

def process_data(frame):
    print('Processing Data...')
    
    radar_cube = dsp.range_processing(frame, window_type_1d=dsp.Window.BARTLETT)
    print(radar_cube)
    assert radar_cube.shape == (numChirpsPerFrame, numRxAntennas, numADCSamples), "[ERROR] Radar cube is not the correct shape!"
    
    radar_cube_dB = 20 * np.log10(np.abs(radar_cube))
    print(radar_cube_dB)

    


def main():
    cmd_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime\RunCustomScripts.cmd'
    studio_runtime_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime'

    subprocess.Popen(cmd_path, cwd=studio_runtime_path)
    
    time.sleep(110)

    dca = DCA1000()
    while True:
        adc_data = dca.read()
        print(adc_data)
        #process_data(adc_data)


if __name__ == "__main__":
    main()






