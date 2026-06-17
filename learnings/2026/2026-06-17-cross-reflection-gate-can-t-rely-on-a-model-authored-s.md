---
id: 2026-06-17-cross-reflection-gate-can-t-rely-on-a-model-authored-s
date: '2026-06-17'
studio: cross
engagement: viz-and-learnings
category: orchestration
severity: medium
title: reflection gate can't rely on a model-authored session_id marker
proposed-change: SessionStart hook writes the id-keyed marker; Producer touches a
  plain activity file; gate compares mtimes
status: open
ref: ''
---

## What happened

Planned the Producer to drop .studios/run-<session_id>, but the model doesn't know its own session_id. Reworked so SessionStart (which gets session_id on stdin) owns the keyed marker and the Producer only touches an activity file.

## Why it matters (tool, not deliverable)

_(why this is about the studio/plugin itself)_

## Proposed change

SessionStart hook writes the id-keyed marker; Producer touches a plain activity file; gate compares mtimes

## Promotion

_(filled when promoted → issue # or ADR-NNN)_
