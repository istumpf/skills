## 1. State and validation

- [ ] 1.1 Implement new_state() and item normalization.
- [ ] 1.2 Add relevant tests and run the whole suite.

## 2. Receipts

- [ ] 2.1 Implement receive(state, site, sku, qty, event).
- [ ] 2.2 Add relevant tests and run the whole suite.

## 3. Reservations

- [ ] 3.1 Implement reserve(state, order, site, items, expires, now).
- [ ] 3.2 Add relevant tests and run the whole suite.

## 4. Lifecycle

- [ ] 4.1 Implement sweep(state, now) and cancel(state, order).
- [ ] 4.2 Add relevant tests and run the whole suite.

## 5. Shipment

- [ ] 5.1 Implement ship(state, order, now).
- [ ] 5.2 Add relevant tests and run the whole suite.

## 6. Transfers

- [ ] 6.1 Implement transfer(state, source, target, sku, qty, now).
- [ ] 6.2 Add relevant tests and run the whole suite.

## 7. Bundles

- [ ] 7.1 Implement reserve_bundle(state, order, site, bundles, catalog, expires, now).
- [ ] 7.2 Add relevant tests and run the whole suite.

## 8. Snapshots

- [ ] 8.1 Implement dump_state(state) and load_state(text).
- [ ] 8.2 Add relevant tests and run the whole suite.

## 9. Atomic batches

- [ ] 9.1 Implement apply_batch(state, commands, now).
- [ ] 9.2 Add relevant tests and run the whole suite.

## 10. Backorder policy

- [ ] 10.1 Obtain stakeholder decision on replenishment priority; only then specify and implement backorders.
- [ ] 10.2 Add relevant tests and run the whole suite.
