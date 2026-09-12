# Public media provenance

The website uses three stills extracted from `video-web.mp4`, the prototype demonstration supplied by Edwin Kestler in this project discussion. The source video is low resolution; the stills are documentation, not performance measurements.

| Public derivative | Extracted source | Description |
|---|---|---|
| `robot-patio.webp` | `frame_01.jpg` | Rover operating over coffee beans |
| `patio.webp` | `frame_02.jpg` | Rover beside the coffee/concrete boundary |
| `prototype.webp` | `frame_03.jpg` | Another view of the physical rover |

The original recording date is not independently verified. None of these stills establishes the software revision running on the robot or demonstrates the newer Cosmos/student integration. The captions make that boundary explicit.

The site builder copies explicit approved public derivatives only. The raw originals and private bucket remain private; the owner has authorized the two short web previews below.

Derivatives are re-encoded without original EXIF/GPS metadata. The owner retains applicable media rights; the code license is not a blanket license for third-party marks or media. No generated robot image is presented as physical evidence.

[View the prototype still](https://edwinkestler.github.io/caferoomba/assets/prototype.webp).

## Looping dataset previews

These are full-duration web transcodes of the selected raw-data files, not altered demonstrations. The original frame order and playback speed are retained; resolution/bitrate are reduced, audio and metadata are removed, and originals are unchanged. No reverse playback, synthetic interpolation, added labels, or seamless-loop crossfade is applied.

| View | Public file | Duration | Bytes | Source |
|---|---|---|---|---|
| FPV-designated sample | `fpv-sample.mp4` | 10.04 s | 2,403,400 | `data/raw/fpv/runid001/video-ae5e8a55-14f8-4564-8c6d-2955eef4474a.mp4` |
| External-view sample | `external-sample.mp4` | 15.04 s | 3,531,124 | `data/raw/external/runid004/grok-video-06d34419-cff8-4579-b487-9695fc3a5375.mp4` |

The strict limit is **less than 9,000,000 bytes per clip**. Their combined encoded video size is 5,934,524 bytes. Both have H.264 video with no audio; the player is muted, looped, inline and has native controls. Reduced-motion/data-saving preferences pause automatic playback, and offscreen players pause to limit resource use.

**Viewpoint and acquisition caveat:** the FPV folder designation is supplied by the owner, but the selected clip shows the rover from behind. Do not treat it as verified onboard-camera training data. The external source filename contains `grok-video`; filenames and visual plausibility do not establish camera acquisition or generation provenance. Both samples are presented as dataset previews with provenance unverified, not validated real-world autonomy evidence. Confirm origin and synchronization before admitting either to a training/evaluation set.

Source/derivative SHA-256 hashes, byte sizes, original relative paths and transformation notes are recorded in [`site/media.json`](../site/media.json). A copy ships as `assets/media.json` for public provenance. No access to GCS is needed to play the previews.

## Architecture illustrations

`training-pipeline.svg` and `physical-ai-cycle.svg` are explanatory concept graphics with exact vector labels. The training diagram includes a small AI-generated concept vignette; it is not a photograph of the actual robot or hardware. The graphics depict intended workflows, not a completed cloud run or validated autonomy. The second flow treats memory as task history, not automatic online retraining.

The exact architecture and lifecycle are also readable as text on the page and in [This Experiment](EXPERIMENT.md). Full-size SVG links are provided for detailed inspection.
