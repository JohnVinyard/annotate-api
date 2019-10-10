This `featurebot` computes the classic Short-Time Fourier Transform for each 
sound.

![STFT](https://cochlea-example-app-images.s3.amazonaws.com/stft_bot.png)

The bot first downsamples the audio to 11025 hz and converts to mono.  It 
computes features with the following metadata:

```json
{metadata}
```