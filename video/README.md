# Video Artifact

## More Code Is Not Progress

This HyperFrames project produces the companion video for Codex Demo Day Arena: a 2:45 technical documentary-style walkthrough of the control plane, evidence gates, compute allocation loop, and no-winner decision.

## Outputs

- Final MP4: [`renders/more-code-is-not-progress.mp4`](renders/more-code-is-not-progress.mp4)
- Composition source: [`index.html`](index.html)
- Narration script: [`SCRIPT.md`](SCRIPT.md)
- Narration audio: [`assets/narration.mp3`](assets/narration.mp3), generated with Kokoro-ONNX `am_michael`
- Music bed: [`assets/music-bed.mp3`](assets/music-bed.mp3), generated locally with [`generate_music_bed.py`](generate_music_bed.py)
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

The underscore is an original, restrained ambient score generated locally from deterministic synthesis: slow pads, sparse bell tones, a faint low pulse, and filtered texture. It is intentionally mixed under the narration in `index.html` with `data-volume="0.34"` so the final artifact feels cinematic without becoming a pitch-deck hype reel.

To regenerate it:

```bash
python3 generate_music_bed.py
ffmpeg -y -i assets/music-bed.wav \
  -af "highpass=f=60,lowpass=f=8500,acompressor=threshold=-22dB:ratio=1.8:attack=80:release=850,afade=t=in:st=0:d=5,afade=t=out:st=158:d=7,volume=1.15" \
  -codec:a libmp3lame -b:a 192k assets/music-bed.mp3
rm -f assets/music-bed.wav
```
