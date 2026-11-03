## Context

A small Python library receives sequences of tags.

## Goals / Non-Goals

Goals: normalize and deduplicate string tags deterministically without mutating caller input.
Non-goals: non-string inputs and external packages.

## Decisions

Use two functions: `normalize_tags(tags)` retains duplicates; `unique_tags(tags)` builds on normalization and keeps the first occurrence. Both return lists.

## Risks / Trade-offs

Python lowercase semantics apply; no locale-specific normalization is required.
