# Website publication handover — 2026-09-12 UTC

> **Historical publication handover.** The original handover below describes
> publication commit `258e785...` and its then-dirty local checkout. It is kept
> as a point-in-time record; those branch and Project Memory statements are not
> current instructions.

## Current reconciliation

Published main is now `cd0bb2d485831c6b040f933d7ee87ca22b2569f8`.
Website [run 34710087793](https://github.com/EdwinKestler/caferoomba/actions/runs/34710087793)
successfully built, checked and deployed that revision. The repository now also
contains the Real FPV Colab training, portable runtime and runtime portability
review guides.

The allowlist/navigation update that exposes those three guides is a later local
documentation change until it is committed and pushed. A successful local site
test does not publish it; publication requires a succeeding Pages workflow for
the resulting revision.

## Original handover

Project website: https://edwinkestler.github.io/caferoomba/
Documentation library: https://edwinkestler.github.io/caferoomba/docs/index.html
Published main commit: `258e785bd15277b59be9b86df0891aeb0e4e8eae`.
Publication workflow: https://github.com/EdwinKestler/caferoomba/actions/runs/34662814741

## Completed

Website and documentation were committed through the authorized GitHub connector.
GitHub Actions build, publication tests, link checks and Pages deployment succeeded.
The live homepage was retrieved through Remote Desktop Commander on andorxps.
There are 22 rendered documentation guides plus the landing page and 404 page.
Sandbox checks validated 908 internal references and 3 publication tests.
Desktop/mobile rendered-page checks passed for the homepage and selected guides.

## Local checkout boundary

The local branch remains `feat/orin-shadow-integration` with prior uncommitted code.
No robot source, dependencies, hardware settings or private bucket data were changed by this publication.
The terminal execution guard blocked later commands, so local fetch/merge of the published website/docs was not performed.
Do not blindly pull into the dirty checkout. Review the documentation-only commits and reconcile after preserving local work.

## Project Memory

Session: `d52c3a939870fce55adc9b8b2176e115`.
The cache was consulted, reindexed and deeply validated before publication work; final reindex/session-close/consolidate remain pending because terminal execution was blocked.
