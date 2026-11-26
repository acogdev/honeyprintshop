# Honey Print Shop implementation notes

## Current implementation

- The homepage shows only the eight newest Etsy listings.
- `/featured/` shows the shop's Etsy-featured listings, in the order returned by Etsy. It is included in the header navigation.
- Collection routes are `/collections/diabetes-awareness/`, `/collections/book-lovers/`, and `/collections/lifes-adventures/` ("Life's Adventures").
- The Collections dropdown links to the overview and each of the three collection pages.
- `/store/` remains a full listing gallery page, but there is no Store tab in the header. The header has a Shop on Etsy button.
- The main gallery cards are square. Their title and alt text use the decoded Etsy title up to its first comma or pipe; the Etsy label is not displayed.
- The About content remains unchanged. The existing analytics script remains unchanged; no analytics were added.

## Etsy sync and current data

- Run `uv run --no-project --python 3.12 python scripts/sync_etsy.py` locally. It uses Etsy's public API to fetch active listings, the featured listing set/order, and each listing's primary image. It writes `data/etsy/listings.json` and `assets/etsy/`. Hugo builds and deploys do not call Etsy.
- Required environment names are `ETSY_API_KEY`, `ETSY_SHARED_SECRET`, and `ETSY_OWN_SHOP_ID`. The root `.env` is ignored by Git; do not copy credentials into source or CI.
- The sync sends API credentials only to Etsy's Open API. Image downloads use unauthenticated HTTPS requests to the Etsy static-image hosts.
- The sync intentionally omits prices, descriptions, update timestamps, and Etsy alt text. It stores one primary image per active listing, not every listing photo.
- The sync prunes inactive listing image directories and stale image files for active listings.
- The featured endpoint request is capped at 20 results; active listings are paginated separately without that cap.
- The checked-in listing snapshot contains 26 active listings and 8 featured listings. Counts and featured membership can change on subsequent syncs.
- Confirmed Etsy section mapping and latest active counts:
  - `56624970` ("Diabetes") -> `diabetes-awareness` (4 listings)
  - `56641381` ("Book Lovers") -> `book-lovers` (13 listings)
  - `59294210` ("Life's Adventures") -> `lifes-adventures` (9 listings)
- The primary thumbnails are 570x570 JPEGs. The eight original files under `assets/designs/` remain in the repository but are not used by the new Etsy-backed galleries.
- Etsy's featured endpoint was tested successfully. Its returned order is saved as `featured_order`; the Featured page currently displays the eight returned IDs in that order (up to the 20-item request cap).

## Theme and build notes

- Hugo uses Paige v0.111.1 from `_vendor`; CI pins Hugo 0.147.8. Do not edit `_vendor`.
- The existing Paige header and `head-last` overrides remain in use. The header renders the configured menu and the Shop on Etsy CTA. The stylesheet is loaded through `head-last`.
- Paige emits Open Graph and Twitter metadata, but its links partial does not emit a canonical link. Local overrides add canonicals, collection JSON-LD and social images.
- `hugo --minify --cleanDestinationDir --gc` passes with Hugo 0.147.8 and Dart Sass. Dart Sass emits upstream Bootstrap deprecation warnings. The Etsy sync unit tests pass.
- `robots.txt` and `sitemap.xml` are generated. Lighthouse 13.5.0 mobile scores (Performance/Accessibility/SEO) on the current local build: homepage 98/100/100, Store 98/100/100, Diabetes Awareness 99/100/100, Book Lovers 99/100/100, and Life's Adventures 96/100/100.
- The internal link/resource audit checked 431 references across 11 generated HTML pages with no broken paths or fragments. The Docker image build passed against the generated site. The GitHub workflow is tag-triggered and was not run.

## Remaining work

- Phase 3 implementation is complete: canonical URLs are present on every generated HTML page, collection pages include CollectionPage/ItemList JSON-LD without offers or prices, and collection social metadata uses the first local listing image. Pinterest share links are omitted at the owner's request.
- Breadcrumbs are intentionally disabled in `hugo.toml`.
- The collection introduction copy has been reviewed and approved by the owner.
- An About page photo remains optional owner input.
