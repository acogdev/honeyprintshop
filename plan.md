# Honey Print Shop gallery planning

## Goal

Build a static, data-driven gallery that sends visitors to Etsy listings; add pages for Diabetes Awareness, Book Lovers, and Adventure & Travel; refresh the homepage and Store page; and cover accessibility, SEO, social sharing, and an easy authoring workflow. Keep the existing visual style, do not edit `_vendor`, do not deploy, and do not invent product data. Use flagged placeholders when owner data is missing.

## Repo findings

- Repository was clean on `main`; no implementation changes were made.
- Hugo site uses Paige v0.111.1 via vendored Hugo modules. CI pins Hugo 0.147.8; local Hugo is 0.169.0.
- Existing content: homepage, Store, About. Homepage uses Paige gallery/image shortcodes for two images in each of three collections. Store is currently a one-line Etsy link.
- Existing theme overrides are `layouts/partials/paige/site-header.html`, `page.html`, and `head-last.html`. Preserve the custom header/logo and use theme override hooks; never edit `_vendor`.
- Paige supports menu dropdowns. The custom header reads `site.Menus.main`.
- Paige already generates Open Graph and Twitter metadata. Its links partial does not emit a canonical `<link>`, so add canonical markup without duplicating existing OG/Twitter tags.
- `hugo.toml` enables `robots.txt`; Hugo's default sitemap behavior should be checked in the generated site.
- `layouts/partials/paige/head-last.html` currently loads an analytics script from `analytics.acogdev.com`. Owner chose to defer this decision; leave it unchanged for now and add no analytics.
- There are eight source images in `assets/designs/`, not six: `adventure.png`, `adventure2.png`, `bibliophile.png`, `bolus for donuts.png`, `dream impossible.png`, `kindness.png`, `thats not how this works.png`, and `who’s afraid.png`. All are portrait, approximately 1555/1556 × 2000. `dream impossible.png` is about 1.7 MB. Confirm active status, collection, title, alt text, and cover-vs-flat role before migration. Avoid blindly square-cropping portrait artwork.

## Owner data / blockers

- User supplied two Etsy section URLs:
  - `https://www.etsy.com/shop/HoneyThePrintShop?section_id=56641381`
  - `https://www.etsy.com/shop/HoneyThePrintShop?section_id=59294210`
- Their mapping to the three collections is unknown; no third section URL or individual listing URLs were provided.
- Etsy shop and both section pages returned HTTP 403 from the available web fetch and direct curl paths, so active listings could not be verified. Do not infer listing URLs. The plan permits clearly marked placeholders until the owner supplies data.
- User did not provide the requested asset/listing mapping; use placeholders and list them clearly in the PR description unless supplied later.

## Implementation recommendations / caveats

- A design bundle with `build.render: never` can support a data-driven gallery without creating product pages. However, Pinterest's `url` parameter must point to a real published page (such as the collection or Store page), not the non-rendered design page. Alternatively, publish individual design pages if that behavior is desired.
- Collection-page `Product` entries without offers may be valid Schema.org markup but are not guaranteed to qualify for Google Product rich results. Treat structured-data validation separately from rich-result eligibility.
- Keep static/JS-disabled behavior; shortcode can call a shared gallery partial. Use Hugo image processing and ensure the actual rendered/cropped composition preserves the artwork.
- Preserve Paige-generated OG/Twitter metadata; extend the head using the existing hook. Add canonical links explicitly.
- Keep existing analytics script unchanged pending owner decision.
- Validate using the CI Hugo version (0.147.8), including the requested minified/clean build and Docker/workflow checks when implementation is resumed. Lighthouse goals should be measured, not promised before checking the existing analytics and generated image payloads.

## Proposed phases from the owner plan

1. Data model, archetype, card/gallery partials and CSS; migrate confirmed designs; rebuild Store.
2. Collection pages and homepage; menu navigation and Etsy CTA.
3. SEO, JSON-LD, OG image selection, Pinterest links, and README authoring workflow.
4. Optional later work: lightbox, JS filtering, or design-creation script.

The gallery itself has not been implemented or deployed. Resume by confirming the image inventory and Etsy URL/section mapping (or proceeding with explicit placeholders), then implement in small phases.
