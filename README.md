# Honey Print Shop

Welcome to the Honey Print Shop project! This is a landing page type website built using Hugo, a fast and flexible static site generator.

## Building and Testing

To build for release:

`hugo --minify --cleanDestinationDir --gc`

To run for testing:

`hugo serve`

## Etsy listing sync

The site remains static: sync Etsy data locally before building the site. Put
`ETSY_API_KEY`, `ETSY_SHARED_SECRET`, and `ETSY_OWN_SHOP_ID` in the root `.env`
file (or set them in the shell), then run:

`uv run --no-project --python 3.12 python scripts/sync_etsy.py`

The command downloads the primary image for each active listing into
`assets/etsy/` and writes listing metadata (without prices) and Etsy featured
status to `data/etsy/listings.json`. The section-to-collection mapping is
configured in `hugo.toml`; listings in other sections remain available in the
Store. It does not run as part of Hugo or deployment, so Etsy credentials are
never needed by the site build.

Each sync prunes images for inactive listings and stale files for active
listings. It requests up to 20 featured listings, while all active listings
continue to paginate normally.