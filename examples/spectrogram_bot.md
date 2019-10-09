![Mel Spectrogram](https://cochlea-example-app-images.s3.amazonaws.com/spectrogram_bot.png)

This `featurebot` computes perceptually-motivated spectrograms using a bank of 
filters spaced evenly along the [Mel scale](https://en.wikipedia.org/wiki/Mel_scale).  
A logarithmic, [decibel-like](https://en.wikipedia.org/wiki/Decibel) scaling is then applied to the amplitudes.

The bot first downsamples the audio to 11025 hz and converts to mono.  It 
computes features with the following metadata:

```json
{metadata}
```
