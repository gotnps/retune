from typing import Iterable
from grpc.aio import ServicerContext
from google.protobuf.json_format import MessageToDict

from pbs.speech2text_pb2_grpc import GowajeeSpeechToTextServicer
from pbs.speech2text_pb2 import (
    TranscriptionResult,
    TranscribeConfig,
    TranscribeRequest,
    TranscribeResponse,
    StreamingTranscribeConfig,
    StreamingTranscribeRequest,
    StreamingTranscribeResponse,
    WordInfo,
)

import grpc
import numpy as np
from pydub import AudioSegment
from omegaconf import OmegaConf
from recognizer import SpeechRecognizer
from utils import audiosegment_to_librosawav, validate_input, DecodeType

import soxr
import scipy.io.wavfile as wav
import time

import io
import numpy as np
import torch
torch.set_num_threads(1)
import torchaudio
import matplotlib
import matplotlib.pylab as plt
# torchaudio.set_audio_backend("soundfile")
# import pyaudio

model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=True)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

# Taken from utils_vad.py
def validate(model,
             inputs: torch.Tensor):
    with torch.no_grad():
        outs = model(inputs)
    return outs

# Provided by Alexander Veysov
def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/32768
    sound = sound.squeeze()  # depends on the use case
    return sound

voiced_confidences = []
# MAX_BUFFER = 81920 * 3  # 8192*2*5
NUM_PREV_RESULT = 5 # 3
MAX_LENGTH_AUDIO_BUFF = 96000 * 10 # 3
# RESET_CUTOFF_NUM = 5
# MAX_BUFFER = 49152 # 8192*2*3
class GowajeeSpeechRecognizerService(GowajeeSpeechToTextServicer):
    def __init__(self, config_path: str = "local_configs.yaml"):
        configs = OmegaConf.load(config_path)
        self.configs = configs
        self.recognizer = SpeechRecognizer(configs.recognizer)
        print('init')

    def Transcribe(
        self, request: TranscribeRequest, context: ServicerContext
    ) -> TranscribeResponse:
        config = MessageToDict(request.config)
        decoder_type = config.get("decoderType", "LMBeamSearch")
        get_timestamps = config.get("getWordTimestamps", False)
        get_speaking_rate = config.get("getSpeakingRate", False)
        word_list = config.get("wordList", None)

        audio_data = request.audio_data
        temp_file, error_message = validate_input(audio_data, decoder_type)
        if error_message != "":
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(error_message)
            return TranscribeResponse()

        sound = AudioSegment.from_file(temp_file).set_channels(1).set_frame_rate(8000)
        signal_array = audiosegment_to_librosawav(sound)

        results = self.recognizer.infer(
            signal_array,
            8000,
            DecodeType[decoder_type],
            get_timestamps=get_timestamps,
            get_speak_rate=get_speaking_rate,
            hotwords=word_list,
        )
        print('enter transcribe fn')

        return TranscribeResponse(
            results=[
                TranscriptionResult(
                    transcript=result.get("transcript", None),
                    start_time=result.get("start_time", None),
                    end_time=result.get("end_time", None),
                    speaking_rate=result.get("speaking_rate", None),
                    word_timestamps=[
                        WordInfo(
                            word=item.get("word", None),
                            start_time=item.get("start_time", None),
                            end_time=item.get("end_time", None),
                            confidence=item.get("confidence", None),
                        )
                        for item in result.get("word_timestamps", [])
                    ],
                )
                for result in results
            ]
        )

    def StreamingTranscribe(
        self,
        request_iterator: Iterable[StreamingTranscribeRequest],
        context: ServicerContext,
    ) -> Iterable[StreamingTranscribeResponse]:

        # print("Start") ## Debugging, Delete This line on production pharse
        audio_buffer = b""
        #### Add-on
        long_audio_buffer = b""
        cutoff_transcript = [None] * NUM_PREV_RESULT # [""] * NUM_PREV_RESULT ## contain a previous transcript for cutting the audio
        next_idx = 0 ## contain the next index of the cutoff result
        cutoff = False
        ####
        prev_results = list()
        offset_time = 0
        reset_cutoff = 0
        old_speaking_confidence = 0
        for request in request_iterator:
            # print(len(request.audio_data))
            # print(request) ## Debugging, Delete This line on production pharse

            is_final_option = request.is_final
            config = MessageToDict(request.streaming_config)
            transcribe_config = config.get("transcribeConfig", {})
            get_timestamps = transcribe_config.get("getWordTimestamps", False)
            get_speaking_rate = transcribe_config.get("getSpeakingRate", False)
            word_list = transcribe_config.get("wordList", None)

            ### Add-on is_final: is_final will be true if the audio_buffer is over the capability
            is_final = False
            if cutoff:
                is_final = True
                
                # Add-on if the lastest result is empty string dont send them back
                # print("RESULT:", (''.join(list(map(lambda x: x['transcript'], results)))).strip())
                if (''.join(list(map(lambda x: x['transcript'], results)))).strip() == "":
                    cutoff = False
                    audio_buffer = b""
                    # print("--------------------------")
                    continue
                #################################

                if len(results) > 1:
                    last_segment = results[-1]
                    # idx = int(
                    #     (last_segment["start_time"] - offset_time)
                    #     * config.get("sampleRate")
                    #     * 2
                    # )
                    idx = -1
                    audio_buffer = b"" # audio_buffer[idx:]
                    prev_results = results # results[:-1] # the previous version, we add the result to the prev_results
                    offset_time = prev_results[-1]["end_time"]
                    
                    final_response = self.create_response(results, get_timestamps, True)
                    # final_response = self.create_response(results[:-1], get_timestamps, True)
                else:
                    audio_buffer = b""
                    if len(results) == 1:
                        prev_results = results
                    if prev_results: # prevent list out of range in the early state
                        offset_time = prev_results[-1]["end_time"]
                    else:
                        offset_time = 0
                    
                    final_response = self.create_response(results, get_timestamps, True)
                ## Add-on reset recognizer
                # reset_cutoff += 1
                # if reset_cutoff % RESET_CUTOFF_NUM == 0:
                #     self.recognizer = SpeechRecognizer(self.configs.recognizer)
                ##########################
                # print("--------------------------")
                yield final_response
                
            cutoff = False
            if len(request.audio_data) == 0:
                continue

            #### Add-on
            long_audio_buffer += request.audio_data
            print('len(long_audio_buffer) : ', len(long_audio_buffer))
            print("long_audio_buffer : ")
            print(long_audio_buffer)
            ## The more value, the less time that it will predict in one second.
            if len(long_audio_buffer) <= 29000:  # 15000, 12000: #UNCOMMENT
                continue
            ####

            # audio_buffer += request.audio_data
            chunk = long_audio_buffer
            audio_buffer += long_audio_buffer
            long_audio_buffer = b""
            

#             try:
#                 signal_array = np.frombuffer(audio_buffer, dtype=np.int16).reshape(-1)
#                 # print("Config", config.get("sampleRate"))

#                 results = self.recognizer.infer(
#                     signal_array,
#                     sample_rate=config.get("sampleRate"),
#                     decoder_type=transcribe_config.get("decoderType", "LMBeamSearch"),
#                     get_timestamps=True,
#                     get_speak_rate=get_speaking_rate,
#                     hotwords=word_list,
#                 )

#             except Exception as e:
#                 print("ERROR", e)
#                 pass
            signal_array = np.frombuffer(audio_buffer, dtype=np.int16).reshape(-1)
            audio_int16 = np.frombuffer(chunk, dtype=np.int16)
            # wav.write('test_evaluation.wav', 44100, signal_array)
            # print("Config", config.get("sampleRate"))

            # print("Transcribe")
#             start_time = time.time()
            audio_float32 = int2float(audio_int16)
    
            # get the confidences and add them to the list to plot them later
            current_speaking_confidence = model(torch.from_numpy(audio_float32), 8000).item()
            voiced_confidences.append(current_speaking_confidence)

#             print(voiced_confidences)
            
            if old_speaking_confidence - current_speaking_confidence > 0.2 :
                results = self.recognizer.infer(
                    signal_array,
                    sample_rate=config.get("sampleRate"),
                    decoder_type=transcribe_config.get("decoderType", "LMBeamSearch"),
                    get_timestamps=True,
                    get_speak_rate=get_speaking_rate,
                    hotwords=word_list,
                )
                # results_transcript = ''.join(list(map(lambda x: x['transcript'], results)))
                cutoff = True
#                 print(results_transcript,speaking_confidence)
#                 print('xxx')
          
            if current_speaking_confidence > 0.1:
                # print('talking')
                print(current_speaking_confidence)
            
            old_speaking_confidence = current_speaking_confidence
            # print(cutoff)

#             try:
#                 infer_freq = start_time - end_time
#                 print("transcribe_freq", infer_freq)
#             except:
#                 print("first transcribe")
            
#             end_time = time.time()
#             lm_time = end_time - start_time
#             print("lm_time :", lm_time)
            # print(results)
            
            # Add-on: same transcript cutoff
#             results_transcript = ''.join(list(map(lambda x: x['transcript'], results)))
#             prev_index = (next_idx - NUM_PREV_RESULT + 1) % NUM_PREV_RESULT
#             if results_transcript == cutoff_transcript[prev_index] or len(audio_buffer) >= MAX_LENGTH_AUDIO_BUFF:
#                 cutoff = True
#                 cutoff_transcript = [None] * NUM_PREV_RESULT  # reset previous transcripts
#                 # print("Cutoff:", cutoff)
#                 continue # UNCOMMENT 
#             else:
#                 cutoff = False

#             cutoff_transcript[next_idx % NUM_PREV_RESULT] = results_transcript
#             next_idx = (next_idx + 1) % NUM_PREV_RESULT
            # print(cutoff_transcript)
            ##################################

            # fix time
            if len(prev_results) > 0:
                for i, result in enumerate(results):
                    result["start_time"] = result["start_time"] + offset_time
                    result["end_time"] = result["end_time"] + offset_time

                    if "word_timestamps" in result.keys():
                        for i, item in enumerate(result["word_timestamps"]):
                            item["start_time"] = item["start_time"] + offset_time
                            item["end_time"] = item["end_time"] + offset_time
                            result["word_timestamps"][i] = item

#             if not is_final_option:
#                 streaming_response = self.create_response(prev_results + results, get_timestamps)
#             else:
#                 streaming_response = self.create_response(results, get_timestamps, is_final)
                
#             yield streaming_response
            # config: TranscribeConfig = request_iterator.config

        # pass
        
    def create_response(self, transcription, get_timestamps, is_final=False):
        return StreamingTranscribeResponse(
                    results=[
                        TranscriptionResult(
                            transcript=result.get("transcript", None),
                            start_time=result.get("start_time", None),
                            end_time=result.get("end_time", None),
                            speaking_rate=result.get("speaking_rate", None),
                            word_timestamps=[
                                WordInfo(
                                    word=item.get("word", None),
                                    start_time=item.get("start_time", None),
                                    end_time=item.get("end_time", None),
                                    confidence=item.get("confidence", None),
                                )
                                for item in result.get("word_timestamps", [])
                            ]
                            if get_timestamps
                            else None,
                        )
                        for result in transcription
                    ],
                    is_final = is_final
                )
