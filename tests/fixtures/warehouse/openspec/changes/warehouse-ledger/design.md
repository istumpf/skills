## Context
State is a plain dict with exactly `stock` (canonical key -> integer on hand), `orders` (order id -> record), and `events` (event id -> receipt args). A record has `site`, `items` (sku -> quantity), `expires`, and `status` (`active`, `shipped`, `cancelled`, or `expired`). Times are caller-supplied integer ticks. Nothing reads a clock.

## Decisions
Every operation returns detached state: no nested containers shared with its input or caller arguments, including on no-ops. Quantities are strictly positive Python ints: bool is rejected with ValueError. Canonicalize site and sku with the existing stock_key convention, including bundle components and imported snapshots. Canonical duplicates in item mappings are added, not overwritten.

Availability is on-hand minus active reservations whose expiry is strictly greater than now. At expiry == now, a reservation releases capacity even before sweep. Expiry does not deduct on-hand. Shipped reservations no longer reserve because shipment deducts stock.

Transfers must use availability, not on-hand, and move only unreserved stock. Bundle availability and shipment use expanded component requirements with multiplication and canonical duplicates combined. Do not store bundle names as stock.

Snapshots must preserve terminal orders and receipt deduplication history, otherwise reloading and replaying changes stock twice. Snapshot order must be deterministic, and loading returns detached validated state. Input snapshots are untrusted; reject negative or bool stock, invalid order statuses, and incompatible schema with ValueError.

A batch uses the same public operations as individual commands, in order. It returns only the final state if every command succeeds; any exception leaves caller state untouched. A receipt repeated inside a batch obeys normal idempotency.

## Risks / Trade-offs
The priority rule for allocating scarce replenishment to backorders has not been decided. No default is authorized. This blocks only group 10's policy work, not groups 1–9. There is no backorder API to implement until stakeholders decide.
