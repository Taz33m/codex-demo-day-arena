# Pivot Policy

Pivots are allowed. Thrashing is not.

## Rule

A team may pivot when the current company is less fundable than a sharper adjacent company, and the pivot can be demonstrated with equal or stronger product evidence.

## Allowed Pivots

Allowed:

- narrowing the buyer,
- changing the wedge inside the same market,
- replacing a weak workflow with a more painful adjacent workflow,
- turning a generic tool into a specific system of record or workflow engine,
- moving from CLI-only demo to a buyer-relevant product surface,
- changing architecture to support a more credible product.

Not allowed:

- switching because implementation got hard,
- abandoning working product evidence for a prettier story,
- renaming the company without changing the painful workflow,
- pivoting into a generic AI wrapper,
- hiding that the repo changed direction,
- deleting tests/evals/receipts to make the pivot easier.

## Timing

Before video gate:

- pivots are allowed if they improve investability,
- a pivot must preserve or rebuild `make demo`, `make test`, `make eval`, and `make receipt`,
- the repo must write a short `PIVOT_DECISION.md`.

After video gate:

- only wedge sharpening is allowed,
- major pivots require failing the video gate and re-entering product work.

## Required Pivot Record

If a team pivots, `PIVOT_DECISION.md` must answer:

1. What was the old company?
2. What is the new company?
3. Why is the new customer pain stronger?
4. What product evidence carries over?
5. What product evidence must be rebuilt?
6. What did the team stop doing?
7. Why does this increase the chance of a $10M investment?

The pivot is valid only when the product contract passes again.
