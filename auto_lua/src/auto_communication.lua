-------- CONSTANTS ----------------------------------------
COM_PORT=6
BAUDRATE= 115200

RADARSS_BIN_PATH =  "C:\\ti\\mmwave_studio_02_01_01_00\\rf_eval_firmware\\radarss\\xwr68xx_radarss.bin"
MASTERSS_BIN_PATH = "C:\\ti\\mmwave_studio_02_01_01_00\\rf_eval_firmware\\masterss\\xwr68xx_masterss.bin"

-----------------------------------------------------------

-------- RADAR SETTINGS -----------------------------------
-- General
NUM_TX = 2
NUM_RX = 4

-- ProfileConfig
START_FREQ = 60 -- GHz
IDLE_TIME = 100 -- us
RAMP_END_TIME = 60 -- us
ADC_START_TIME = 6 --us
FREQ_SLOPE = 29,982 -- MHz/us
ADC_SAMPLES = 256 -- ADC Samples originally 256
SAMPLE_RATE = 10000 -- ksps
RX_GAIN = 30 -- dB was orginially 30
TX_START_TIME = 0

-- FrameConfig
START_CHIRP_TX = 0
END_CHIRP_TX = 1 
NUM_FRAMES = 0 -- Set this to 0 to continuously stream data
CHIRP_LOOPS = 128 
PERIODICITY = 40 -- ms
-----------------------------------------------------------

-------- INIT ---------------------------------------------

dofile("C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\Scripts\\AR1xInit.lua")
ar1.selectRadarMode(0)
ar1.selectCascadeMode(0)
ar1.FullReset()
ar1.SOPControl(2)
ar1.Connect(COM_PORT,BAUDRATE,1000)
ar1.Calling_IsConnected()
-----------------------------------------------------------

-------- DEVICE SETTINGS ----------------------------------
ar1.frequencyBandSelection("60G")
ar1.SelectChipVersion("IWR6843")
ar1.deviceVariantSelection("IWR6843")
-----------------------------------------------------------

-------- DOWNLOAD FIRMARE ---------------------------------
ar1.DownloadBSSFw(RADARSS_BIN_PATH)
ar1.GetBSSFwVersion()
ar1.DownloadMSSFw(MASTERSS_BIN_PATH)
ar1.GetMSSFwVersion()
ar1.PowerOn(0, 1000, 0, 0)
ar1.RfEnable()
ar1.GetMSSFwVersion()
ar1.GetBSSFwVersion()
-----------------------------------------------------------

-------- STATIC CONFIG ------------------------------------
ar1.ChanNAdcConfig(1, 1, 0, 1, 1, 1, 1, 2, 1, 0)
ar1.LPModConfig(0, 0)
ar1.RfInit()
-----------------------------------------------------------

-------- DATA CONFIG --------------------------------------
ar1.DataPathConfig(513, 1216644097, 0)
ar1.LvdsClkConfig(1, 1)
ar1.LVDSLaneConfig(0, 1, 1, 0, 0, 1, 0, 0)
-----------------------------------------------------------

-------- SENSOR CONFIG ------------------------------------
ar1.ProfileConfig(0, 60, 100, 6, 60, 0, 0, 0, 0, 0, 0, 29.982, 0, 256, 10000, 0, 131072, 30)
ar1.ChirpConfig(0, 0, 0, 0, 0, 0, 0, 1, 0, 0)
ar1.DisableTestSource(0)
ar1.FrameConfig(0, 0, 0, 128, 40, 0, 0, 1)
-----------------------------------------------------------

-------- ETHERNET -----------------------------------------
ar1.CaptureCardConfig_ResetFPGA()
ar1.selectRadarMode(0)
ar1.GetCaptureCardDllVersion()
ar1.SelectCaptureDevice("DCA1000")
ar1.CaptureCardConfig_EthInit("192.168.33.30", "192.168.33.180", "12:34:56:78:90:12", 4096, 4098)
ar1.CaptureCardConfig_Mode(1, 2, 1, 2, 3, 30)
ar1.CaptureCardConfig_PacketDelay(25)
ar1.GetCaptureCardFPGAVersion()
-----------------------------------------------------------

-------- CAPTURE DATA -------------------------------------
ar1.CaptureCardConfig_StartRecord("C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\PostProc\\adc_data_post_crash.bin", 0)

ar1.StartFrame()
os.execute("timeout /t 2 /nobreak")
--ar1.StopFrame()
--os.execute("timeout /t 3 /nobreak")
--ar1.StartMatlabPostProc("C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\PostProc\\auto_collection\\adc_data.bin")
-----------------------------------------------------------
