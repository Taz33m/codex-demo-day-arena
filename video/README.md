# Video Artifact

## More Code Is Not Progress

This HyperFrames project produces the companion video for Codex Demo Day Arena: a 2:45 technical documentary-style walkthrough of the control plane, evidence gates, compute allocation loop, and no-winner decision.

## Outputs

- Final MP4: [`renders/more-code-is-not-progress.mp4`](renders/more-code-is-not-progress.mp4)
- Composition source: [`index.html`](index.html)
- Narration script: [`SCRIPT.md`](SCRIPT.md)
- Narration audio: [`assets/narration.mp3`](assets/narration.mp3), generated with Kokoro-ONNX `am_michael`
- Music bed: [`assets/music-bed.mp3`](assets/music-bed.mp3), generated locally with FFmpeg
- Visual direction: [`DESIGN.md`](DESIGN.md)
- Shotlist: [`SHOTLIST.md`](SHOTLIST.md)

## Build

```bash
npx hyperframes tts narration.txt --voice am_michael --speed 0.79 --output assets/narration.wav
ffmpeg -y -i assets/narration.wav -codec:a libmp3lame -b:a 160k assets/narration.mp3
rm -f assets/narration.wav
npx hyperframes lint
npx hyperframes validate
npx hyperframes inspect --samples 20
npx hyperframes render --quality standard --fps 30 --workers 1 --output renders/more-code-is-not-progress.mp4
```

The composition intentionally uses one continuous track rather than splitting each beat into sub-compositions, so HyperFrames reports one non-blocking `timeline_track_too_dense` warning. This is accepted to avoid a PowerPoint-like structure.

## Music Bed

The underscore is a restrained, procedural ambient bed generated from FFmpeg sine and pink-noise sources. It is intentionally mixed under the narration in `index.html` with `data-volume="0.16"` so the final artifact feels cinematic without becoming a pitch-deck hype reel.

To regenerate it:

```bash
ffmpeg -y \
  -f lavfi -i "sine=frequency=110:duration=165:sample_rate=48000" \
  -f lavfi -i "sine=frequency=164.81:duration=165:sample_rate=48000" \
  -f lavfi -i "sine=frequency=220:duration=165:sample_rate=48000" \
  -f lavfi -i "sine=frequency=329.63:duration=165:sample_rate=48000" \
  -f lavfi -i "sine=frequency=440:duration=165:sample_rate=48000" \
  -f lavfi -i "anoisesrc=color=pink:duration=165:sample_rate=48000:amplitude=0.08" \
  -filter_complex "[0:a]volume=0.045,tremolo=f=0.10:d=0.22[a0];[1:a]volume=0.030,tremolo=f=0.12:d=0.20[a1];[2:a]volume=0.020,tremolo=f=0.11:d=0.18[a2];[3:a]volume=0.014,tremolo=f=0.13:d=0.14[a3];[4:a]volume=0.008,tremolo=f=0.15:d=0.10[a4];[5:a]lowpass=f=900,highpass=f=90,volume=0.014[a5];[a0][a1][a2][a3][a4][a5]amix=inputs=6:duration=longest:normalize=0,acompressor=threshold=-24dB:ratio=2.2:attack=80:release=900,aecho=0.8:0.35:1200:0.15,afade=t=in:st=0:d=7,afade=t=out:st=158:d=7,volume=0.75[a]" \
  -map "[a]" -codec:a libmp3lame -b:a 128k assets/music-bed.mp3
```
