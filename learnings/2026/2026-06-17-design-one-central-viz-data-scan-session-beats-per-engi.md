---
id: 2026-06-17-design-one-central-viz-data-scan-session-beats-per-engi
date: '2026-06-17'
studio: design
engagement: viz-and-learnings
category: cli
severity: low
title: one central viz_data.scan_session beats per-engine CSV seams
proposed-change: keep the single scan_session call in render.render; don't thread
  data_dir through each engine
status: open
ref: ''
---

## What happened

Every engine writes to the same outputs/ dir, so one scan_session call after the engine covers all exports with far less signature churn than the planned 3 per-engine seams + tuple returns.

## Why it matters (tool, not deliverable)

_(why this is about the studio/plugin itself)_

## Proposed change

keep the single scan_session call in render.render; don't thread data_dir through each engine

## Promotion

_(filled when promoted → issue # or ADR-NNN)_
