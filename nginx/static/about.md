# Cochlea Example Application
This is an example web application built atop the [cochlea API](https://github.com/JohnVinyard/annotate-api), which allows users, both automated and human, to annotate audio from the internet using textual tags or arbitrary numerical data.

The application provides a browse-able interface that closely mirrors the
structure of the cochlea API  and leverages annotations or features from various
automated users. Using this app, you can browse:

- [Annotations](annotations), which attach tags or other arbitrary data to segments of audio
- [Sounds](sounds) belonging to various [datasets](users?userType=dataset)
- [Users](users), both human and automated

In addition to human users who can create textual annotations, two types
of automated user create the foundation of this web app:

## Feature Bots

Automated [feature bots](users?userType=featurebot) users typically stream sounds or
annotations and compute dense numerical features for each one.  Many of these
provide alternative visualizations of a sound, beyond the traditional raw audio
waveform display.  Examples include:
- [stft_bot](users/stft_bot), which computes [short-time fourier transforms](https://en.wikipedia.org/wiki/Short-time_Fourier_transform)
- [chroma_bot](users/chroma_bot), which computes [chroma features](https://en.wikipedia.org/wiki/Chroma_feature)
- [mfcc_bot](users/mfcc_bot), which computes [Mel-frequency cepstral coefficients or MFCCs](https://en.wikipedia.org/wiki/Mel-frequency_cepstrum)

![spectrogram](https://cochlea-example-app-images.s3.amazonaws.com/spectrogram_bot.png)

## Aggregators
Automated [aggregators](users?userType=aggregator) stream sounds or annotations to
create alternative indexes over the data.  In this app, the
[spatial_index](users/spatial_index) user computes embeddings for short segments
of audio that place each segment on a sphere, which allows for the exploration
of similar sounds via a Google Maps-like interface.  Read a [blog post](http://johnvinyard.github.io/zounds/search/embeddings/neural-networks/pytorch/2019/02/22/unsupervised-semantic-audio-embeddings.html) about the
technique or check out the [paper](https://arxiv.org/abs/1711.02209) that inspired it.

![visual explorer](/static/visual_explorer.jpg)
