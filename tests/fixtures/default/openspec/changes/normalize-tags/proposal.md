## Why

Callers need consistent tag normalization and deduplication.

## What Changes

- Add normalization that strips surrounding whitespace, lowercases tags, and discards empty tags.
- Add order-preserving deduplication of normalized tags.

## Capabilities

### New Capabilities
- `tag-normalization`: Normalize and deduplicate a sequence of string tags.

### Modified Capabilities

None.

## Impact

Only the Python module `tags.py` and its tests are affected.
