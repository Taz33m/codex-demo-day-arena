# Candidate State Transitions

| From | To | Condition |
| --- | --- | --- |
| `raw_candidate` | `structurally_ready` | Validator flags cleared. |
| `structurally_ready` | `buyer_compelling` | Buyer-usefulness score and verdict pass the synthetic rubric. |
| `structurally_ready` | `hold` | Repository is runnable but buyer usefulness is weak. |
| `buyer_compelling` | `funded_compute` | Compute allocation policy approves another owner round. |
| `buyer_compelling` | `external_proof_required` | Product is compelling, but the next belief requires external data or users. |
| `funded_compute` | `external_proof_required` | Funded sprint reaches the synthetic development ceiling. |
| `external_proof_required` | `proof_now` | Proof feasibility is high enough for immediate external validation. |
| `external_proof_required` | `proof_later` | Candidate is promising, but the proof path is slower. |
| `external_proof_required` | `customer_data_required` | Candidate cannot advance without partner/customer data. |
| `external_proof_required` | `synthetic_ceiling` | No credible near-term proof path exists. |
| `proof_now` | `IC_ready` | External evidence is acquired. |
| `proof_now` | `no_winner` | External evidence is missing. |
| `IC_ready` | `invest` | IC approves funding despite remaining flaws. |
| `IC_ready` | `no_winner` | IC rejects the candidate. |
