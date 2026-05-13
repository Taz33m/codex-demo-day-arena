# Compute Allocation

Compute allocation is the portfolio policy for deciding which repos deserve another agent round.

## Inputs

- validator readiness,
- buyer-usefulness score,
- product maturity flags,
- external-proof blockers,
- current portfolio rank.

## Actions

- `round-2-owner`: fund another repo-owner sprint.
- `external-proof-required`: freeze local coding until real proof appears.
- `hold`: structurally ready but not worth more compute now.
- `salvage-or-pivot`: validator is not green; normal compute is blocked.

## Principle

Additional compute should be granted only when the next round can change a specific investor belief.
