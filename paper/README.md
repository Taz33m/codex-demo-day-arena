# Technical Paper

## More Code Is Not Progress

**Evidence-Gated Orchestration for AI Coding Agent Product Portfolios**

This paper presents Codex Demo Day Arena as a control-plane system for AI-agent portfolio governance. The central claim is simple: when AI coding agents can generate product-shaped repos quickly, the hard problem becomes deciding which candidates deserve more compute.

## Read

- [PDF](more-code-is-not-progress.pdf)
- [Full paper](more-code-is-not-progress.md)
- [LaTeX source](more-code-is-not-progress.tex)
- [References and repo artifacts](references.md)

## Build

```bash
cd paper
make
```

The build uses `tectonic`.

## Figures

- [Control-plane architecture](figures/control-plane.mmd)
- [Candidate state machine](figures/candidate-state-machine.mmd)

## Tables

- [Portfolio results](tables/portfolio-results.md)
- [State transitions](tables/state-transitions.md)
- [Proof-now finalists](tables/proof-finalists.md)
- [Gate definitions](tables/gates.md)
- [Failure modes](tables/failure-modes.md)

## Citation

```bibtex
@misc{mahashin2026morecode,
  title = {More Code Is Not Progress: Evidence-Gated Orchestration for AI Coding Agent Product Portfolios},
  author = {Tazeem Mahashin},
  year = {2026},
  howpublished = {GitHub repository},
  url = {https://github.com/Taz33m/codex-demo-day-arena}
}
```
