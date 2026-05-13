# Product Maturity Rubric

This rubric exists because a credible seed-stage product cannot look like a thin script plus a story.

## Technical Product Reality: 45

| Category | Points |
| --- | ---: |
| Core domain engine models the painful workflow | 10 |
| Input ingestion, normalization, and validation | 6 |
| Generated outputs derive from inputs, not pasted fixtures | 8 |
| Product surface is buyer-relevant and demoable | 7 |
| Tests and evals cover non-happy-path cases | 7 |
| Architecture can plausibly extend to production integrations | 5 |
| Mocks and boundaries are explicit | 2 |

## Product/Business Investability: 35

| Category | Points |
| --- | ---: |
| Painkiller problem | 8 |
| Specific buyer and wedge | 8 |
| Product aha moment | 7 |
| Distribution and revenue logic | 5 |
| Market upside | 4 |
| Honest risk handling | 3 |

## Comparative IC Strength: 20

| Category | Points |
| --- | ---: |
| Stronger than other repos on wedge clarity | 5 |
| Stronger than other repos on product reality | 6 |
| Stronger than other repos on market pull | 4 |
| Stronger than other repos on defensibility path | 3 |
| Stop/pivot decision quality | 2 |

## Hard No-Invest Gates

A repo cannot be investable if any are true:

- demo does not run,
- no meaningful domain logic,
- outputs are hardcoded or pasted,
- no eval or test harness,
- mocks are hidden,
- committed secrets exist,
- product surface is only a pitch artifact,
- the repo cannot explain why it is a company instead of a feature,
- technical maturity score is below threshold.

## Python-Heavy Repos

Python-heavy is acceptable when it reflects domain depth: parsers, scoring systems, workflow engines, eval harnesses, and batch artifacts.

Python-heavy is not acceptable when it means the product is only:

- one script,
- one happy-path fixture,
- no operator workflow,
- no product surface,
- no integration-shaped boundaries,
- no durable evidence.

Round 1 repo owners should preserve strong Python engines but add product maturity where it matters: clearer workflow surfaces, richer evals, cleaner architecture, better outputs, and a credible path to production.
