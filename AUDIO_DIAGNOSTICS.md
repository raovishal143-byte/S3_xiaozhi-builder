# Audio diagnostics

The build workflow patches the pinned XiaoZhi audio service to log rate-limited OPUS_RX, OPUS_DECODE, PCM_OUTPUT and I2S_WRITE events. I2S_WRITE reports the actual bytes_written value returned by i2s_channel_write.
