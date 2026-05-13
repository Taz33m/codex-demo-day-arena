# Compute Allocation Policy

Only fundable products receive more compute.

The arena is a startup foundry simulator, not an infinite build queue. Repos earn additional owner rounds by becoming more technically real and more investable.

## Tiers

### Tier 1: Near Fundable

These repos have a green product contract and either clear the maturity validator or have one or two high-leverage gaps.

Default action: continue.

### Tier 2: Interesting Engine, Needs Product Surface

These repos have a real domain engine and useful artifacts, but the buyer/operator product layer or investment-readiness answer is weak.

Default action: one focused owner round.

### Tier 3: Weak Or Toy-Like

These repos have multiple maturity failures. They may be interesting, but more compute requires a clear pivot or salvage thesis.

Default action: require pivot/continue justification before another full owner round.

### Tier 4: Archive / Merge Candidate

These repos fail the product contract, lack useful artifacts, or cannot explain why they are a company instead of a feature.

Default action: archive, kill, or merge into a stronger repo.

## Two-Round Rule

After two owner rounds, every repo must be one of:

- continue,
- pivot,
- archive,
- merge into another repo.

No repo receives a third owner round merely because it made substantial progress. It must show investment progress.

## Compute Law

Product work is funded by evidence:

- working demo,
- buyer-relevant surface,
- useful receipt artifact,
- meaningful evals,
- clear wedge,
- honest investment-readiness decision.

Engineering mass without fundability progress does not earn more compute.

## Next Round Requests

A repo that asks for another round must create `NEXT_ROUND_REQUEST.md` and answer:

- current state,
- remaining flags,
- proposed next work,
- funding delta,
- kill criteria.

No next round is granted unless the funding delta could change an investment decision.

## Tier 3 / Tier 4

Tier 3 repos must create `SALVAGE_OR_PIVOT_MEMO.md` before receiving normal owner compute.

Tier 4 repos receive no owner compute. Allowed actions are archive, merge useful components, or extract lessons.
