import codecs
import socket
import struct
from enum import Enum
import numpy as np

class CMD(Enum):
    RESET_FPGA_CMD_CODE = '0100'
    RESET_AR_DEV_CMD_CODE = '0200'
    CONFIG_FPGA_GEN_CMD_CODE = '0300'
    CONFIG_EEPROM_CMD_CODE = '0400'
    RECORD_START_CMD_CODE = '0500'
    RECORD_STOP_CMD_CODE = '0600'
    PLAYBACK_START_CMD_CODE = '0700'
    PLAYBACK_STOP_CMD_CODE = '0800'
    SYSTEM_CONNECT_CMD_CODE = '0900'
    SYSTEM_ERROR_CMD_CODE = '0a00'
    CONFIG_PACKET_DATA_CMD_CODE = '0b00'
    CONFIG_DATA_MODE_AR_DEV_CMD_CODE = '0c00'
    INIT_FPGA_PLAYBACK_CMD_CODE = '0d00'
    READ_FPGA_VERSION_CMD_CODE = '0e00'

    def __str__(self):
        return str(self.value)

# MESSAGE = codecs.decode(b'5aa509000000aaee', 'hex')

class DCA1000:
    def __init__(self, config, static_ip, adc_ip, data_port, config_port):
        self.config = config
        self.cfg_dest = (adc_ip, config_port)
        self.cfg_recv = (static_ip, config_port)
        self.data_recv = (static_ip, data_port)

        self.config_socket = socket.socket(socket.AF_INET,
                                           socket.SOCK_DGRAM,
                                           socket.IPPROTO_UDP)
        self.data_socket = socket.socket(socket.AF_INET,
                                         socket.SOCK_DGRAM,
                                         socket.IPPROTO_UDP)

        self.data_socket.bind(self.data_recv)

        self.config_socket.bind(self.cfg_recv)

        self.data = []
        self.packet_count = []
        self.byte_count = []

        self.frame_buff = []

        self.curr_buff = None
        self.last_frame = None

        self.lost_packets = None
        self.num_chirps = self.config['radar']['chirps']
        self.num_rx = self.config['radar']['num_rx_antennas']
        self.num_samples = self.config['radar']['num_adc_samples']
        self.num_lanes = self.config['radar']['num_lvds_lanes'] 
        self.iq_swap = self.config['radar']['iq_swap']   
        self.ch_interleave = self.config['radar']['ch_interleave']

        self.BYTES_IN_FRAME = self.config['dca1000']['dataSizeOneFrame'] # 524288
        self.BYTES_IN_FRAME_CLIPPED = (self.BYTES_IN_FRAME // self.config['dca1000']['BYTES_IN_PACKET']) * self.config['dca1000']['BYTES_IN_PACKET'] # 524160
        
        self.PACKETS_IN_FRAME = self.BYTES_IN_FRAME / self.config['dca1000']['BYTES_IN_PACKET'] #360.09
        self.PACKETS_IN_FRAME_CLIPPED = self.BYTES_IN_FRAME // self.config['dca1000']['BYTES_IN_PACKET'] #360
        
        self.UINT16_IN_PACKET = self.config['dca1000']['BYTES_IN_PACKET'] // 2 #728 data points of 16 bits (I + Q) in one packet
        self.UINT16_IN_FRAME = self.BYTES_IN_FRAME // 2 # 262144 data points of 16 bits in one frame

    def write_to_file(self, data):
        with open(self.config['paths']['output_file'], 'a') as f:
            f.write(data + '\n')

    def configure(self):
        # SYSTEM_CONNECT_CMD_CODE
        # 5a a5 09 00 00 00 aa ee
        print(self._send_command(CMD.SYSTEM_CONNECT_CMD_CODE))

        # READ_FPGA_VERSION_CMD_CODE
        # 5a a5 0e 00 00 00 aa ee
        print(self._send_command(CMD.READ_FPGA_VERSION_CMD_CODE))

        # CONFIG_FPGA_GEN_CMD_CODE
        # 5a a5 03 00 06 00 01 02 01 02 03 1e aa ee
        print(self._send_command(CMD.CONFIG_FPGA_GEN_CMD_CODE, '0600', 'c005350c0000'))

        # CONFIG_PACKET_DATA_CMD_CODE 
        # 5a a5 0b 00 06 00 c0 05 35 0c 00 00 aa ee
        print(self._send_command(CMD.CONFIG_PACKET_DATA_CMD_CODE, '0600', 'c005350c0000'))

    def close(self):
        self.data_socket.close()
        self.config_socket.close()

    def read(self, timeout=1):
        self.data_socket.settimeout(timeout)
        ret_frame = np.zeros(self.UINT16_IN_FRAME, dtype=np.float32)
        while True:
            packet_num, byte_count, packet_data = self._read_data_packet()
            if byte_count % self.BYTES_IN_FRAME_CLIPPED == 0:
                packets_read = 1
                ret_frame[0:self.UINT16_IN_PACKET] = packet_data
                break

        while True:
            packet_num, byte_count, packet_data = self._read_data_packet()
            packets_read += 1

            if byte_count % self.BYTES_IN_FRAME_CLIPPED == 0:
                self.lost_packets = self.PACKETS_IN_FRAME_CLIPPED - packets_read
                return ret_frame

            curr_idx = ((packet_num - 1) % self.PACKETS_IN_FRAME_CLIPPED)
            try:
                ret_frame[curr_idx * self.UINT16_IN_PACKET:(curr_idx + 1) * self.UINT16_IN_PACKET] = packet_data
            except:
                pass

            if packets_read > self.PACKETS_IN_FRAME_CLIPPED:
                packets_read = 0
    
    def _read_data_packet(self):
        data, _ = self.data_socket.recvfrom(self.config['dca1000']['MAX_PACKET_SIZE'])
        packet_num = struct.unpack('<1l', data[:4])[0]
        byte_count = struct.unpack('>Q', b'\x00\x00' + data[4:10][::-1])[0]
        packet_data = np.frombuffer(data[10:], dtype=np.uint16).astype(np.float32)
        packet_data = (packet_data.astype(np.int16)).astype(np.float32)
        return packet_num, byte_count, packet_data

    def send_command(self, cmd, length='0000', body='', timeout=1):
        self.config_socket.settimeout(timeout)

        resp = ''
        msg = codecs.decode(''.join((self.config['dca1000']['CONFIG_HEADER'], str(cmd), length, body, self.config['dca1000']['CONFIG_FOOTER'])), 'hex')
        try:
            self.config_socket.sendto(msg, self.cfg_dest)
            resp, addr = self.config_socket.recvfrom(self.config['dca1000']['MAX_PACKET_SIZE'])
        except socket.timeout as e:
            print(e)
        return resp

    

    def _listen_for_error(self):
        self.config_socket.settimeout(None)
        msg = self.config_socket.recvfrom(self.config['dca1000']['MAX_PACKET_SIZE'])
        if msg == b'5aa50a000300aaee':
            print('stopped:', msg)

    def _stop_stream(self):
        return self._send_command(CMD.RECORD_STOP_CMD_CODE)

    def dp_reshape2LaneLVDS(raw_data):
        raw_data_4 = raw_data.reshape(4, -1)
        raw_data_I = raw_data_4[:2, :].reshape(-1, order='F')
        raw_data_Q = raw_data_4[2:, :].reshape(-1, order='F')
        frame_data = np.column_stack((raw_data_I, raw_data_Q))
        return frame_data
    
    def generate_frame_data(self, raw_data):
        if self.num_lanes == 2:
            frame_data = self.dp_reshape2LaneLVDS(raw_data)
        else:
            raise ValueError(f"{self.num_lanes} LVDS lanes are not supported")

        #switch ReIm to ImRe
        if self.iq_swap == 1:
            frame_data[:, [0, 1]] = frame_data[:, [1, 0]]

        frame_complex = frame_data[:, 0] + 1j * frame_data[:, 1]

        frame_complex = frame_complex.reshape(self.num_chirps, self.num_rx, self.num_samples)

        if self.ch_interleave == 1:
            frame_complex = frame_complex.transpose(0, 2, 1)

        return frame_complex.astype(np.single)
    
    @staticmethod
    def organize(raw_frame, num_chirps, num_rx, num_samples):   
        ret = np.zeros(len(raw_frame) // 2, dtype=complex)

        # Separate IQ data
        ret[0::2] = raw_frame[0::4] + 1j * raw_frame[2::4]
        ret[1::2] = raw_frame[1::4] + 1j * raw_frame[3::4]
        return ret.reshape((num_chirps, num_rx, num_samples))

    
    
