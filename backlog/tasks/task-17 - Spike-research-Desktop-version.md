---
id: TASK-17
title: 'Spike research: Desktop version'
status: Done
assignee:
  - '@kimi'
created_date: '2026-07-31 18:06'
updated_date: '2026-07-31 18:16'
labels: []
dependencies: []
documentation:
  - doc-2
type: spike
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Research if we can make a version where we essentially have a lightweight desktop app that runs these dashboards the same as we have it now. What are our options? What is the effort / benefits of each approach. Also note; it needs to stay cross platform.

I know Kotlin/JJetpack Compose well, but would also be happy with other proposals
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Research the current architecture (hub = Python stdlib HTTP server + HTML UI, dashboards = spawned 'backlog browser' processes embedded via iframes).
2. Evaluate desktop-app options against that architecture: pywebview wrapper, Tauri, Electron, Kotlin Compose Desktop (+ KCEF webview), PWA.
3. For each: effort, benefits, drawbacks, cross-platform story, distribution/installer story, and how it interacts with the existing Python hub and spawned backlog processes.
4. Write findings as a backlog doc, link it to this task, and give a recommendation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Research complete. Findings written to doc-2: evaluated pywebview, Tauri, Electron, Kotlin Compose Desktop (webview + native variants), and PWA baseline against the current architecture (Python stdlib hub + spawned backlog browser processes embedded via iframes). Recommendation: pywebview + PyInstaller wrapper (option 1) as the lightweight, lowest-effort path; Tauri as the upgrade path for distribution polish; Compose Desktop noted as viable but poor effort/benefit today (no official CMP webview, KCEF archived Nov 2025).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Spike complete. Research documented in doc-2 (linked). Evaluated 6 options against the current architecture: pywebview+PyInstaller, Tauri, Electron, Kotlin Compose Desktop (webview and native variants), and a PWA baseline. Recommendation: pywebview wrapper around the existing hub (lightweight, days of effort, single-language), with Tauri as the upgrade path for distribution polish. Kotlin/Compose route assessed as viable but weak effort/benefit today (no official CMP desktop webview; KCEF archived Nov 2025). Evidence: findings verified against the codebase (dashboard_hub/server.py, backlog_browser.py, doc-1 decision) and current ecosystem facts via web sources cited in doc-2. No code changes made; this was research only.
<!-- SECTION:FINAL_SUMMARY:END -->
