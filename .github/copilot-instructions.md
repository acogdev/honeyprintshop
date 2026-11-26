# Honey Print Shop repository instructions

## What this repository does

This is a static Hugo site for Honey Print Shop. It showcases Etsy listings and links visitors to Etsy; it does not process orders or run an application server.

- `/` shows the eight newest active listings.
- `/featured/` shows the listings Etsy currently marks as featured, in Etsy's returned order.
- `/collections/` contains the Diabetes Awareness, Book Lovers, and Life's Adventures collections.
- `/store/` contains the full listing gallery. The header intentionally has no Store tab; it has a Shop on Etsy button instead.

## Etsy data

- `scripts/sync_etsy.py` is an explicit local sync. It fetches active listings, featured listing IDs/order, and one primary image per active listing. It writes `data/etsy/listings.json` and `assets/etsy/`.
- The site must remain buildable without network access or Etsy credentials. Never call the Etsy API from Hugo templates, builds, or deployment.
- The sync makes live API requests and rewrites generated data/assets. Run it only when requested or required for the task.
- Do not fetch, store, display, or add schema markup for Etsy prices. Do not invent listing URLs, section mappings, or product claims.
- Section ID to collection mappings live in `hugo.toml`. Unmapped active listings remain in the Store gallery.
- Listing titles are HTML-entity-decoded during sync. In cards, display the title up to the first comma or pipe; use that same text for image alt text.
- Keep Etsy credentials in the ignored root `.env` or the environment. Never print, copy, commit, or include them in generated site data.

## Hugo and theme conventions

- Use Hugo Extended 0.147.8 (the CI version) and Dart Sass for builds.
- Build with `hugo --minify --cleanDestinationDir --gc`; run the local site with `hugo serve`.
- Never edit `_vendor`. Extend Paige through files under `layouts/` and `assets/`.
- Reuse the existing HPS gallery partials and shortcode instead of duplicating card markup.
- Keep the gallery static and functional without JavaScript. Preserve square image cards, consistent title areas, responsive image processing, visible keyboard focus, and reduced-motion support.
- Preserve the current Paige theme, logo, colors, dark-mode behavior, and existing analytics configuration. Do not add analytics or change deployment behavior unless asked.
- Keep `plan.md` and `plan-notes.md` aligned with material changes to routes, data flow, or scope.

## Python conventions

- Run every Python command through `uv`; do not invoke `python`, `python3`, `pip`, or `pytest` directly.
- This repository has no Python project manifest and the sync currently uses only the standard library. Use `uv run --no-project --python 3.12`:

  ```sh
  uv run --no-project --python 3.12 python scripts/sync_etsy.py
  uv run --no-project --python 3.12 python -m unittest discover -s scripts -p 'test_*.py'
  ```

- Do not add Python dependencies for functionality available in the standard library. If dependencies become necessary, add and maintain them with `uv` in `pyproject.toml` and `uv.lock`, then use `uv run` for execution.
- Keep sync operations idempotent and avoid logging credentials or unrelated environment variables.

## Validation

- For Hugo/template/content changes, run the CI-version Hugo build.
- For Python changes, run the focused unittest suite through `uv`.
- Run Docker or workflow checks when the change affects generated output or build/deploy configuration.
- Do not claim Lighthouse, SEO rich-result, or full link-audit acceptance until those checks have actually been run.
