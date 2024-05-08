import matplotlib.pyplot as plt
import numpy as np

class RadarPlot:
    def __init__(self, numRangeBins):
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.line, = self.ax.plot([], [], '-o', label='Radar Output dB')
        self.ax.set_xlim(0, numRangeBins - 1)
        self.ax.set_ylim(-20, 150)
        self.ax.set_title('Radar dB Values')
        self.ax.set_xlabel('Range Bin')
        self.ax.set_ylabel('dB Output')
        self.ax.legend()
        plt.ion()
        plt.show()

    def update_plot(self, radar_cube_dB, chirp_index=0, antenna_index=0):
        """
        Updates the plot with new radar dB data for a single chirp and antenna.
        Args:
            radar_cube_dB (numpy.ndarray): The dB data of the radar cube.
            chirp_index (int): Index of the chirp to display.
            antenna_index (int): Index of the antenna to display.
        """
        try:
            if radar_cube_dB.ndim == 3:
                dB_values = radar_cube_dB[chirp_index, antenna_index, :]
                self.line.set_data(range(len(dB_values)), dB_values)
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
            else:
                print("Data dimension mismatch")
        except IndexError as e:
            print(f"IndexError: {e}")
            print(f"Check chirp_index: {chirp_index}, antenna_index: {antenna_index}")
