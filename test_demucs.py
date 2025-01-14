#!/usr/bin/env python
#
# This file uses Demucs for music source speration, trained on Musdb-HQ
# See https://github.com/facebookresearch/demucs for more information
# The model was trained with the following flags (see the Demucs repo)
# python run.py --channels=48 --musdb=PATH_TO_MUSDB_HQ --is_wav
# **For more information, see**: https://github.com/facebookresearch/demucs/blob/master/docs/mdx.md
#
# NOTE: Demucs needs the model to be submitted along with your code.
# In order to download it, simply run once locally `python test_demucs.py`
#
# Making submission using the pretrained Demucs model:
# 1. Edit the `aicrowd.json` file to set your AICrowd username.
# 2. Submit your code using git-lfs
#    #> git lfs install
#    #> git add models
# 3. Download the pre-trained model by running
#    #> python test_demucs.py
#
# IMPORTANT: if you train your own model, you must follow a different procedure.
# When training is done in Demucs, the `demucs/models/` folder will contain
# the final trained model. Copy this model over to the `models/` folder
# in this repository, and add it to the repo (Make sure you setup git lfs!)
# Then, to load the model, see instructions in `prediction_setup()` hereafter.

import torch.hub
import torch
import torchaudio as ta

from demucs import pretrained
from demucs.utils import apply_model, load_model  # noqa

from evaluator.music_demixing import MusicDemixingPredictor


class DemucsPredictor(MusicDemixingPredictor):
    def prediction_setup(self):
        # Load your model here and put it into `evaluation` mode
        torch.hub.set_dir('./models/')

        # Use a pre-trained model
        self.separator = pretrained.load_pretrained('demucs48_hq')

        # If you want to use your own trained model, copy the final model
        # from demucs/models (NOT demucs/checkpoints!!) into `models/` and then
        # uncomment the following line.

        # self.separator = load_model('models/my_model.th')

        self.separator.eval()

    def prediction(
        self,
        mixture_file_path,
        bass_file_path,
        drums_file_path,
        other_file_path,
        vocals_file_path,
    ):

        # Load mixture
        mix, sr = ta.load(str(mixture_file_path))
        assert sr == self.separator.samplerate
        assert mix.shape[0] == self.separator.audio_channels

        # Normalize track
        mono = mix.mean(0)
        mean = mono.mean()
        std = mono.std()
        mix = (mix - mean) / std

        # Separate
        with torch.no_grad():
            estimates = apply_model(self.separator, mix, shifts=5)
        estimates = estimates * std + mean

        # Store results
        target_file_map = {
            "vocals": vocals_file_path,
            "drums": drums_file_path,
            "bass": bass_file_path,
            "other": other_file_path,
        }
        for target, path in target_file_map.items():
            idx = self.separator.sources.index(target)
            source = estimates[idx]
            mx = source.abs().max()
            if mx >= 1:
                print('clipping', target, mx, std)
            source = source.clamp(-0.99, 0.99)
            ta.save(str(path), source, sample_rate=sr)


if __name__ == "__main__":
    submission = DemucsPredictor()
    submission.run()
    print("Successfully generated predictions!")
