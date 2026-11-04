## ADDED Requirements

### Requirement: State
new_state() SHALL return {"stock": {}, "orders": {}, "events": {}}. Public operations SHALL follow the design validation and detached-state rules.

#### Scenario: Empty ledger
- **WHEN** new_state() is called
- **THEN** all three mappings are empty

### Requirement: Receipts
receive SHALL add qty on hand at the canonical site/sku. event is a globally unique receipt id. Repeating an event with the same canonical site, sku, qty SHALL be a no-op; reusing it with different arguments SHALL raise ValueError.

#### Scenario: Receive stock
- **WHEN** 5 units of A arrive at north with event e1
- **THEN** stock NORTH:A is 5

### Requirement: Reservations
reserve SHALL create a new active order with normalized nonempty items, expires > now, and sufficient available stock for every item. Reusing an order id (including terminal ids), invalid quantities, or insufficient capacity SHALL raise ValueError. It SHALL NOT deduct on-hand.

#### Scenario: Reserve an item
- **WHEN** north has 5 A and a new order reserves 2 A until tick 10 at tick 1
- **THEN** on-hand remains 5 and the order is active

### Requirement: Lifecycle
sweep SHALL mark active orders expired when expires <= now, without changing stock. cancel SHALL mark an active order cancelled; a cancelled order is a detached no-op; cancelling any other status or an unknown id SHALL raise ValueError.

#### Scenario: Cancel order
- **WHEN** an active order is cancelled
- **THEN** its status becomes cancelled and on-hand is unchanged

### Requirement: Shipment
ship SHALL ship only active orders with expires > now, deducting their items exactly once and setting shipped status. A shipped order SHALL be a detached no-op on retry, including after its original expiry. Unknown, cancelled, or expired orders SHALL raise ValueError.

#### Scenario: Ship an order
- **WHEN** an order for 2 A is shipped from an initial stock of 5
- **THEN** 3 A remain and its status is shipped

### Requirement: Transfers
transfer SHALL move qty between distinct canonical sites, using only stock available at now. Invalid quantity, identical sites, or insufficient availability SHALL raise ValueError.

#### Scenario: Move stock
- **WHEN** 3 of 5 unreserved A move from north to south
- **THEN** north has 2 and south has 3

### Requirement: Bundles
catalog maps bundle names to component item mappings. bundles maps bundle names to counts. reserve_bundle SHALL expand quantities and call the reservation rules. Unknown bundles SHALL raise ValueError. Stored order items SHALL contain only canonical component SKUs.

#### Scenario: Reserve bundle
- **WHEN** a kit contains 2 A and 1 B and an order asks for 2 kits
- **THEN** it reserves 4 A and 2 B

### Requirement: Snapshots
dump_state SHALL return compact JSON with sorted object keys and an outer object {"version": SCHEMA_VERSION, "state": state}. load_state SHALL validate and restore it. Imported stock keys and order items SHALL canonicalize and combine duplicates. Other state fields and event semantics SHALL survive a round trip.

#### Scenario: Snapshot roundtrip
- **WHEN** an empty ledger is dumped and loaded
- **THEN** it equals a new empty ledger

### Requirement: Atomic batches
commands SHALL be a sequence of dicts with op and keyword arguments for receive, reserve, sweep, cancel, ship, transfer, or reserve_bundle. apply_batch SHALL supply its now argument only to operations accepting now. Unknown op SHALL raise ValueError. Failure SHALL expose no partial updates.

#### Scenario: Batch two receipts
- **WHEN** a batch receives 2 A then 3 A with different event ids
- **THEN** on-hand is 5

### Requirement: Unresolved policy
Backorder policy SHALL remain unresolved until stakeholder input, with its implementation and verification tasks unchecked. No invented allocation priority SHALL be added.

#### Scenario: Policy unavailable
- **WHEN** no stakeholder decision is available
- **THEN** groups 1–9 can complete while group 10 stays pending
