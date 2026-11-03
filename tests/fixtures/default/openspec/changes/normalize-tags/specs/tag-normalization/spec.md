## ADDED Requirements

### Requirement: Normalize tags
The library SHALL expose `normalize_tags(tags)` that returns stripped lowercase tags in input order, omits empty results, retains duplicates, and does not mutate the input.

#### Scenario: Whitespace and duplicates
- **WHEN** called with `[" A ", "", "a", " B "]`
- **THEN** it returns `["a", "a", "b"]` and leaves the input unchanged

### Requirement: Deduplicate normalized tags
The library SHALL expose `unique_tags(tags)` that normalizes tags and retains only the first occurrence of each tag in order.

#### Scenario: Ordered unique results
- **WHEN** called with `[" B ", "a", "b", " A ", " "]`
- **THEN** it returns `["b", "a"]`
