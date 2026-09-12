# Website maintenance

## Layout

`site/index.html` is the project landing page. `site/assets/` holds CSS, small JavaScript, the favicon, concept diagrams and explicitly curated image/video derivatives. `site/documents.json` is the allowlist of Markdown guides rendered by `scripts/build_site.py`. Output goes to `_site/` and is never built by executing robot modules.

The generator copies only approved assets, renders Markdown with raw HTML disabled, rewrites documentation links, and gives each page a table of contents. Non-allowlisted source links point to GitHub instead of copying arbitrary repository files. No unrestricted raw datasets, credentials, notebook outputs or local memory enter the site. Two explicitly authorized video derivatives are copied from site/assets; the original data folders are never published wholesale.

## Local build

Use an isolated documentation environment, not the robot runtime:

```bash
python3 -m venv .caferoomba/site-venv
.caferoomba/site-venv/bin/python -m pip install -r site/requirements.txt
.caferoomba/site-venv/bin/python scripts/build_site.py
.caferoomba/site-venv/bin/python scripts/check_site.py
.caferoomba/site-venv/bin/python -m http.server 8080 --bind 127.0.0.1 --directory _site
```

Open `http://127.0.0.1:8080/` on that same machine. Stop the server when finished. Mobile layout, keyboard navigation and reduced-motion behavior should be visually checked as well as link validation.

## Publishing

`.github/workflows/pages.yml` builds the allowlisted site, validates it and deploys through GitHub Pages. The Pages setting must use **GitHub Actions** (`build_type=workflow`). Pull-request builds validate but do not deploy. The deployment job requires `pages: write` and `id-token: write`; repository content is read-only during build.

The expected project address is `https://edwinkestler.github.io/caferoomba/`. Verify the actual deployment output and HTTP response before calling an update live. Do not add a custom domain or analytics without a separate owner decision.

## Updating content

Keep `docs/STATUS.md`, the site capability labels and `docs/evidence/publication.json` consistent. Use named revisions for evidence, never aggregate unrelated test counts, and keep historical robot photographs captioned separately from the newer software.

Before publishing, review the explicit file list. Do not include uncommitted runtime changes simply because they share the working directory. Preserve unrelated files and the existing index. Use a documentation-only branch/worktree for publication when necessary.

References: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) and [Pages API](https://docs.github.com/en/rest/pages/pages).

## Updating preview clips and illustrations

Only `fpv-sample.mp4` and `external-sample.mp4` are approved public videos. Each must remain below 9,000,000 bytes and match its SHA-256 entry in `site/media.json`; the site build rejects a mismatch. The link checker rejects other MP4s. Exact `.gitignore` exceptions keep unrelated raw footage ignored.

Preserve the source clips. Regenerate derivatives using FFmpeg H.264, original speed/order, no audio, stripped metadata, yuv420p and faststart. Update the provenance manifest, poster, page size/duration labels and media guide together. Confirm actual viewpoint and acquisition provenance; a folder name is not evidence of camera placement.

The page has `autoplay muted loop playsinline controls`; JavaScript pauses previews for reduced motion, data saving, offscreen state and hidden tabs. The global pause/play control and native player controls remain available. Check playback plus motion preferences in a real browser after a media update.

The SVGs are self-contained concept illustrations, not captured sensor evidence. Markdown image references to approved site assets are rewritten into the generated docs. Keep precise flow labels accessible in HTML as well.

Reference encoding settings are recorded in `site/media.json`: H.264/libx264, CRF 24, maxrate 1800k, bufsize 3600k, 24 fps, 960×644, yuv420p, faststart, no audio and stripped metadata. Automated publication/browser checks are recorded in `docs/evidence/website_media_experiment.json`.
