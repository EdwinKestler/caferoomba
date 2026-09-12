# Website maintenance

## Layout

`site/index.html` is the project landing page. `site/assets/` holds CSS, small JavaScript, the favicon and explicitly curated photographs. `site/documents.json` is the allowlist of Markdown guides rendered by `scripts/build_site.py`. Output goes to `_site/` and is never built by executing robot modules.

The generator copies only approved assets, renders Markdown with raw HTML disabled, rewrites documentation links, and gives each page a table of contents. Non-allowlisted source links point to GitHub instead of copying arbitrary repository files. No raw datasets, credentials, notebook outputs, local memory or private bucket objects enter the site.

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
