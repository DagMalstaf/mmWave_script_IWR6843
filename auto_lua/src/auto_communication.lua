COM_PORT=6
BAUDRATE= 115200

RADARSS_BIN_PATH =  "C:\\ti\\mmwave_studio_02_01_01_00\\rf_eval_firmware\\radarss\\xwr68xx_radarss.bin"
MASTERSS_BIN_PATH = "C:\\ti\\mmwave_studio_02_01_01_00\\rf_eval_firmware\\masterss\\xwr68xx_masterss.bin"

dofile("C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\Scripts\\AR1xInit.lua")
ar1.selectRadarMode(0)
ar1.selectCascadeMode(0)


ar1.FullReset()
ar1.SOPControl(2)
ar1.Connect(COM_PORT,BAUDRATE,1000)
ar1.Calling_IsConnected()

ar1.frequencyBandSelection("60G")
ar1.SelectChipVersion("IWR6843")
ar1.deviceVariantSelection("IWR6843")

ar1.DownloadBSSFw(RADARSS_BIN_PATH)
ar1.GetBSSFwVersion()
ar1.DownloadMSSFw(MASTERSS_BIN_PATH)
ar1.GetMSSFwVersion()

ar1.PowerOn(0, 1000, 0, 0)
ar1.RfEnable()
ar1.GetMSSFwVersion()
ar1.GetBSSFwVersion()

ar1.ChanNAdcConfig(1, 1, 0, 1, 1, 1, 1, 2, 1, 0)
ar1.LPModConfig(0, 0)
ar1.RfInit()

ar1.DataPathConfig(513, 1216644097, 0)
ar1.LvdsClkConfig(1, 1)
ar1.LVDSLaneConfig(0, 1, 1, 0, 0, 1, 0, 0)

ar1.ProfileConfig(0, 60, 100, 6, 60, 0, 0, 0, 0, 0, 0, 29.982, 0, 256, 10000, 0, 131072, 30)
ar1.ChirpConfig(0, 0, 0, 0, 0, 0, 0, 1, 0, 0)
ar1.DisableTestSource(0)
ar1.FrameConfig(0, 0, 8, 128, 40, 0, 0, 1)

ar1.GetCaptureCardDllVersion()
ar1.SelectCaptureDevice("DCA1000")
ar1.CaptureCardConfig_EthInit("192.168.33.30", "192.168.33.180", "12:34:56:78:90:12", 4096, 4098)
ar1.CaptureCardConfig_Mode(1, 2, 1, 2, 3, 30)
ar1.CaptureCardConfig_PacketDelay(25)
ar1.GetCaptureCardFPGAVersion()

ar1.CaptureCardConfig_StartRecord("C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\PostProc\\adc_data_auto.bin", 1)
ar1.StartFrame()
ar1.StopFrame()

ar1.StartMatlabPostProc("C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\PostProc\\adc_data_auto.bin")
