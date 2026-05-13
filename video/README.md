# Video Artifact

## More Code Is Not Progress

This HyperFrames project produces the companion video for Codex Demo Day Arena: a 2:45 technical documentary-style walkthrough of the control plane, evidence gates, compute allocation loop, and no-winner decision.

## Outputs

- Final MP4: [`renders/more-code-is-not-progress.mp4`](renders/more-code-is-not-progress.mp4)
- Composition source: [`index.html`](index.html)
- Narration script: [`SCRIPT.md`](SCRIPT.md)
- Visual direction: [`DESIGN.md`](DESIGN.md)
- Shotlist: [`SHOTLIST.md`](SHOTLIST.md)

## Build

```bash
npx hyperframes lint
npx hyperframes validate
npx hyperframes inspect --samples 20
npx hyperframes render --quality standard --fps 30 --workers 1 --output renders/more-code-is-not-progress.mp4
```

The composition intentionally uses one continuous track rather than splitting each beat into sub-compositions, so HyperFrames reports one non-blocking `timeline_track_too_dense` warning. This is accepted to avoid a PowerPoint-like structure.
