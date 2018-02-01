# -*- coding:utf-8 -*-

import ctypes
import os
import sys
import wave
from platform import system

# 识别正常
USC_ASR_OK = 0
# 有结果返回
USC_RECOGNIZER_PARTIAL_RESULT = 2
# 检测到语音结束
USC_RECOGNIZER_SPEAK_END = 101
# appkey
USC_OPT_ASR_APP_KEY = 9
# 密钥
USC_OPT_USER_SECRET = 204
# 配置音频格式
USC_OPT_INPUT_AUDIO_FORMAT = 1001
# 识别内容域
USC_OPT_RECOGNITION_FIELD = 18

# 配置你自己的key
app_key_str = "appKey"
user_secret_str = "appSecret"


class UnisoundAsr(object):

    def __init__(self):

        self.lib_path = os.path.dirname(os.path.realpath(__file__)) + "/unisound_lib"
        if system() == "Windows":
            self.cdll = ctypes.cdll.LoadLibrary(os.path.join(self.lib_path, 'libusc.dll'))
        else:
            self.cdll = ctypes.cdll.LoadLibrary(os.path.join(self.lib_path, 'libusc.so'))
        self.handle = ctypes.c_longlong(0)
        # 创建实例 usc_create_service
        self.cdll.usc_create_service.argtypes = [ctypes.c_void_p]
        ref_handle = ctypes.byref(self.handle)
        ret = self.cdll.usc_create_service(ref_handle)
        if ret != USC_ASR_OK:
            print('usc_create_service_ext error.. : ', ret)

        # 设置识别AppKey
        app_key = ctypes.c_char_p(app_key_str.encode())
        ret = self.cdll.usc_set_option(self.handle, USC_OPT_ASR_APP_KEY, app_key)
        if ret != USC_ASR_OK:
            print('usc_set_option error ', ret)
        user_secret = ctypes.c_char_p(user_secret_str.encode())
        ret = self.cdll.usc_set_option(self.handle, USC_OPT_USER_SECRET, user_secret)
        if ret != USC_ASR_OK:
            print("usc_set_option error  : ", ret)
        ret = self.cdll.usc_login_service(self.handle)
        if ret != USC_ASR_OK:
            print('usc_login_service error', ret)

    def asr(self, wav_file):
        # 读取文件
        def get_wave_content(file_path):
            with wave.open(file_path, 'rb') as f:
                n = f.getnframes()
                fs = f.getframerate()
                wav_frames = f.readframes(n)
            return wav_frames, fs

        frames, sample_rate = get_wave_content(wav_file)
        return self.asr_buffer(frames, sample_rate)

    def asr_buffer(self, pcm_data, sample_rate):
        info = {}
        pcm_size = len(pcm_data)
        #  开启语音识别
        ret = -1
        if sample_rate == 16000:
            ret = self.cdll.usc_set_option(self.handle, USC_OPT_INPUT_AUDIO_FORMAT, ctypes.c_char_p("pcm16k".encode()))
        elif sample_rate == 8000:
            ret = self.cdll.usc_set_option(self.handle, USC_OPT_INPUT_AUDIO_FORMAT, ctypes.c_char_p("pcm8k".encode()))
        else:
            print("不支持的文件格式")
        if ret != USC_ASR_OK:
            print('usc_set_option error ', ret)
        ret = self.cdll.usc_set_option(self.handle, USC_OPT_RECOGNITION_FIELD, ctypes.c_char_p("general".encode()))
        if ret != USC_ASR_OK:
            print('usc_set_option error ', ret)
        ret = self.cdll.usc_start_recognizer(self.handle)

        if ret != USC_ASR_OK:
            print('usc_start_recognizer error ', ret)
        result_text = ""
        info['error'] = '0'
        stepsize = 640
        for index in range(0, pcm_size, stepsize):
            start_index = index
            end_index = min((index + stepsize), pcm_size)
            data_buffer = ctypes.c_char_p(pcm_data[start_index:end_index])
            ret = self.feed_buffer(data_buffer, end_index - start_index)
            if ret == USC_RECOGNIZER_PARTIAL_RESULT or ret == USC_RECOGNIZER_SPEAK_END:
                # 获取中间部分识别结果
                result_text += self.get_cur_result()
            elif ret < 0:
                info['error'] = str(ret)
                # 网络出现错误退出
                print("usc_feed_buffer error %d\n" % ret)

        # 停止语音输入
        ret = self.cdll.usc_stop_recognizer(self.handle)
        if ret == 0:
            # 获取剩余识别结果
            result_text += self.get_cur_result()
        info['result'] = result_text
        empty_result = "无内容"
        if result_text.strip() == '':
            result_text = empty_result
        return result_text

    # 释放 usc_release_service
    def release_recognizer(self):
        ret = self.cdll.usc_cancel_recognizer(self.handle)
        print('usc_cancel_recognizer %d\n' % ret)
        self.cdll.usc_release_service(self.handle)

    def feed_buffer(self, data_buffer, len_data_buffer):
        self.cdll.usc_feed_buffer.argtypes = [ctypes.c_longlong, ctypes.c_char_p, ctypes.c_int]
        self.cdll.usc_feed_buffer.restype = ctypes.c_int
        return self.cdll.usc_feed_buffer(self.handle, data_buffer, len_data_buffer)

    def get_cur_result(self):
        self.cdll.usc_get_result.argtypes = [ctypes.c_longlong]
        self.cdll.usc_get_result.restype = ctypes.c_char_p
        ret = self.cdll.usc_get_result(self.handle)
        return str(ret, encoding="utf-8")


def main():
    wav_file = sys.argv[1]
    unisound_asr = UnisoundAsr()
    result = unisound_asr.asr(wav_file)
    print(result)
    # unisound_asr.release_recognizer()


if __name__ == '__main__':
    main()
