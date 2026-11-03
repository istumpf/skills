## ADDED Requirements

### Requirement: Successor
The library SHALL expose `successor(n)` returning the next integer.

#### Scenario: Negative integer
- **WHEN** called with -1
- **THEN** it returns 0

### Requirement: Predecessor
The library SHALL expose `predecessor(n)` returning the previous integer.

#### Scenario: Zero
- **WHEN** called with 0
- **THEN** it returns -1
