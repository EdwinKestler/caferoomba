# Documentation

CafeRoomba is an open-source coffee-drying-patio robotics project by Edwin Kestler. Start with the evidence boundary before connecting equipment.

Explore [This Experiment](EXPERIMENT.md) for the local-notebook → Colab Enterprise → onboard policy workflow and the role of cloud compute for a GPU-constrained project.

## Start here

| Guide | Purpose |
|---|---|
| [Status and evidence](STATUS.md) | What exists in public code, what exists only locally, and what remains unverified |
| [Quickstart](QUICKSTART.md) | Reproduce the CPU fixture and inspect a runtime environment |
| [Architecture](ARCHITECTURE.md) | Offline teacher, onboard student, interfaces, data flow, and module ownership |
| [Hardware](HARDWARE.md) | Workstation/Orin distinction, USB/CSI interfaces, and environment isolation |
| [Runtime](ORIN_COMPANION.md) | Safe bring-up, configuration, and known CLI limitations |
| [Portable runtime](PORTABLE_RUNTIME.md) | Supported host/Orin composition, USB profiles and fail-closed deployment procedure |
| [Runtime portability review](RUNTIME_PORTABILITY_REVIEW.md) | Named host, CI and passive-device evidence plus the remaining Orin gates |
| [Mission state machine](FSM.md) | Public FSM, local integration, and the intended mission lifecycle |
| [Safety](SAFETY.md) | Motion boundaries, telemetry freshness, turn clearance, and release gates |

## Develop and evaluate

| Guide | Purpose |
|---|---|
| [Dataset contract](DATASET.md) | Demonstrations, causal clips, labels, splits, and private storage |
| [Real FPV Colab training](COLAB_TRAINING.md) | Reviewed-label preparation, resumable full-data training, evaluation and artifact handoff |
| [Model card](MODEL_CARD.md) | Student inputs, outputs, learning targets, and current limitations |
| [Cosmos teacher](DEPLOYMENT_COSMOS_NIM.md) | Integration contract and the distinction between mock and live inference |
| [Testing](TESTING.md) | Test environments, recorded evidence, regression and hardware gates |
| [Jetson deployment](DEPLOYMENT_JETSON.md) | Native runtime compatibility and target validation |
| [Cloud media](GCS_MEDIA.md) | Local-first recordings and private, versioned object storage |
| [Troubleshooting](TROUBLESHOOTING.md) | Common environment, camera, serial, and model problems |
| [Roadmap](PENDING_WORK.md) | Ordered implementation milestones with acceptance criteria |

## Publish and maintain

[Challenge evidence](CHALLENGE_EVIDENCE.md) · [Project media](MEDIA.md) · [Website maintenance](WEBSITE.md) · [Agent setup](AGENT_SETUP.md) · [Local integration handover](LOCAL_INTEGRATION_STATUS.md) · [Changelog](../CHANGELOG.md) · [Contributing](../CONTRIBUTING.md) · [Security](../SECURITY.md)

The original [Orin integration plan](PLAN_ORIN_AUTONOMY.md) remains a design history, not a claim that all of its stages are complete. [Project Memory](PROJECT_MEMORY.md) remains authoritative for agent workflow, not hardware validation.
