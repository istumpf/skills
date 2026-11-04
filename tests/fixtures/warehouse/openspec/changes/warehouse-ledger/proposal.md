## Why
Operators need an in-memory warehouse ledger that can reserve, ship, and move stock without losing accounting consistency.

## What Changes
Add pure ledger operations, reservation lifecycle, transfers, bundle orders, versioned snapshots, and transactional command batches.

## Capabilities
### New Capabilities
- `warehouse-ledger`: Inventory accounting and reservation workflows.
### Modified Capabilities
None.

## Impact
Only warehouse.py and its unittest tests. Preserve SCHEMA_VERSION and stock_key, including its whitespace/case normalization. No storage, network, CLI, pricing, or automatic replenishment.
