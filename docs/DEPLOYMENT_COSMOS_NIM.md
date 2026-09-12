# Cosmos teacher integration

**Status: planned live integration; mock-only in the published execution path.**

The requested model identifier in source is `nvidia/cosmos3-nano-reasoner`. Verify the actual provider model, endpoint, schema, hardware requirements and terms before an authorized run. This document does not claim a verified endpoint or that a particular GPU can load it.

## What is implemented

`teacher/cosmos.py` provides a deterministic mock annotation path with `is_mock=true`. `annotate_live()` checks configuration and then refuses execution even when credentials exist. Adding an API key alone therefore cannot activate live inference.

The current student training function does not consume those annotations. A completed teacher request and a trained student are separate implementation/evidence milestones.

## Required implementation

1. Explicit backend selection with bounded timeouts, retries, rate limits and approved spending.
2. Causal image/video request encoding that matches the verified provider contract.
3. Strict response schema validation, abstention and malformed-output handling.
4. Content hashes for the actual input bytes, model revision and prompt version; do not rely only on filenames.
5. Human review and masked auxiliary targets for accepted annotations.
6. An evaluation comparing the same student/data split with and without teacher supervision.

The teacher remains offline. The robot must not require cloud connectivity, API credentials, or live reasoning calls to stop safely or follow a local policy.

## Cloud and local execution

The earlier repository records describe an attempted local NIM feasibility check on a desktop GPU; that is not a universal memory-support matrix. Verify the exact backend/model/precision rather than copying an old hardware estimate. Colab Enterprise can orchestrate preparation and student training; teacher inference may need a separate authorized endpoint or compatible GPU environment.

No paid API call, provisioning action, model download with new terms, or private-video upload should be triggered by an ordinary test import.

Primary starting points: [NVIDIA Cosmos repository](https://github.com/NVIDIA/cosmos), [Colab Enterprise documentation](https://cloud.google.com/colab/docs). Record the exact references used by each future run.
