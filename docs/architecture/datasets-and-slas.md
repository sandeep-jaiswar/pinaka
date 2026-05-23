# NSE Dataset Coverage and Ingestion SLAs

## 1. Tiering model

### Tier 0 (must have for MVP screening)
- Daily bhavcopy / price-volume snapshots
- Deliverable quantity and % deliverables
- Corporate actions (split/bonus/dividend)
- Index constituents baseline

### Tier 1 (high-value upgrades)
- Derivatives OI/volume summaries
- Participant-wise stats (FII/DII where available)
- Block/bulk deals

### Tier 2 (later)
- Option chain snapshots
- Additional sentiment/event datasets

## 2. Proposed ingestion matrix

| Dataset | Source path (logical) | Cadence | Partition key | Freshness SLA | Backfill priority |
|---|---|---|---|---|---|
| `bhavcopy_eq` | `nse/capital_market/bhavcopy` | Daily EOD | `trade_date` | T+0 20:00 IST | P0 |
| `deliverable_eq` | `nse/capital_market/deliverable` | Daily EOD | `trade_date` | T+0 21:00 IST | P0 |
| `corp_actions` | `nse/capital_market/corp_actions` | Daily | `event_date` | T+1 10:00 IST | P0 |
| `index_constituents` | `nse/index/constituents` | Daily | `as_of_date` | T+1 08:00 IST | P1 |
| `fo_oi` | `nse/derivatives/oi` | Daily | `trade_date` | T+0 22:00 IST | P1 |
| `block_deals` | `nse/capital_market/block_deals` | Daily | `trade_date` | T+1 09:00 IST | P2 |

## 3. Quality SLOs
- ingestion success rate (7-day rolling): >= 99.0%
- freshness SLO met: >= 98.5%
- schema breakage incidents: 0 unmitigated per month

## 4. Symbol and market calendar strategy
- Maintain a dedicated trading calendar table to avoid attempting loads on market holidays.
- Symbol universe table is versioned daily to ensure reproducible historical screens.

## 5. Late data and correction policy
- Data that arrives after SLA is marked `late_arrival=true`.
- Correction reruns are tracked with `revision_number` in curated tables.
- Gold features are re-materialized for corrected partitions only.
