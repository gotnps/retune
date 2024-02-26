import os
import time
import random
from pydub import AudioSegment
import numpy as np

def insert_noises(input_path, output_path, snr):
    NOISE_FOLDER_PATH = '/Users/got/Documents/retune/t+im/dent/noise'

    real_audio = AudioSegment.from_file(input_path)

    noise_list = os.listdir(NOISE_FOLDER_PATH)
    if '.DS_Store' in noise_list:
        noise_list.remove('.DS_Store')
    noise_list.sort()
    noise_paths = [os.path.join(NOISE_FOLDER_PATH, item) for item in noise_list]
    
    combined_noise = AudioSegment.silent(duration=len(real_audio))
    for i, noise_path in enumerate(noise_paths):
        if i == 1 :
            noise_audio = AudioSegment.from_file(noise_path)
            noise_audio = noise_audio.apply_gain(15)
            start_time = np.random.randint(0, len(noise_audio) - len(real_audio))
            noise_segment = noise_audio[start_time:start_time + len(real_audio)]
            combined_noise = combined_noise.overlay(noise_segment)

        else :
            noise_audio = AudioSegment.from_file(noise_path)
            start_time = np.random.randint(0, len(noise_audio) - len(real_audio))
            noise_segment = noise_audio[start_time:start_time + len(real_audio)]
            combined_noise = combined_noise.overlay(noise_segment)
    
    signal_power = np.sum(np.abs(np.array(real_audio.get_array_of_samples())))
    noise_power = signal_power / (10 ** (snr / 10))

    # Calculate the power of the selected noise segment
    combined_noise_power = np.sum(np.abs(np.array(combined_noise.get_array_of_samples())))

    # Adjust the amplitude of the noise segment to achieve the desired noise power
    combined_noise = combined_noise - (combined_noise.dBFS - 20 * np.log10(noise_power / combined_noise_power))

    # Add the noise segment to the real audio
    noisy_audio = real_audio.overlay(combined_noise)

    noisy_audio.set_frame_rate(8000)
    # Export the result to a new audio file
    noisy_audio.export(output_path, format='mp3')
    # combined_noise.export(output_path, format="mp3")

def process_files(folder_path, snr):
    file_list = os.listdir(folder_path)

    for i, file_name in enumerate(file_list):
        start = time.time()
        file_path = os.path.join(folder_path, file_name)
        output_path = os.path.join(os.path.dirname(folder_path), "data_with_noise", f"{file_name.split('.')[0]}_n.mp3")
        insert_noises(file_path, output_path, snr[i])
        end = time.time()
        duration = end - start
        print(i+1, ',duration:', duration)
        print('snr :', snr[i])


FOLDER_PATH = '/Users/got/Documents/retune/t+im/dent/data_for_AJ'

snr_list = [i for i in range(16) for _ in range(1)]
# for i in range(6):
#     snr_list.append(i*3)

random.shuffle(snr_list)

process_files(FOLDER_PATH, snr_list)