#!/usr/bin/env python3
"""Synchronize active Etsy listings and their images into Hugo data/assets."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API_BASE = "https://openapi.etsy.com/v3/application"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ENV_KEYS = {"ETSY_API_KEY", "ETSY_SHARED_SECRET", "ETSY_OWN_SHOP_ID"}
ROOT = Path(__file__).resolve().parents[1]


class EtsyAPI:
    def __init__(self, api_key: str, shared_secret: str) -> None:
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "HoneyPrintShop-Etsy-Sync/1.0",
            "x-api-key": f"{api_key}:{shared_secret}",
        }
        self.image_headers = {
            "Accept": "image/*",
            "User-Agent": "HoneyPrintShop-Etsy-Sync/1.0",
        }
        self._last_request = 0.0

    def _open(self, url: str, *, image: bool = False):
        for attempt in range(4):
            elapsed = time.monotonic() - self._last_request
            if elapsed < 0.1:
                time.sleep(0.1 - elapsed)
            self._last_request = time.monotonic()
            request = Request(url, headers=self.image_headers if image else self.headers)
            try:
                response = urlopen(request, timeout=30)
            except HTTPError as error:
                if error.code not in RETRY_STATUSES or attempt == 3:
                    raise
                retry_after = error.headers.get("Retry-After")
                try:
                    delay = min(float(retry_after), 30) if retry_after else 2**attempt
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            except URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue

            if not image:
                return response

            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_IMAGE_BYTES:
                response.close()
                raise ValueError(f"Image exceeds {MAX_IMAGE_BYTES} bytes")
            return response

        raise RuntimeError("Etsy request retries exhausted")

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict:
        query = f"?{urlencode(params)}" if params else ""
        with self._open(f"{API_BASE}{path}{query}") as response:
            return json.load(response)

    def download_image(self, url: str, path: Path) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not (
            parsed.hostname == "etsystatic.com"
            or (parsed.hostname or "").endswith(".etsystatic.com")
        ):
            raise ValueError(f"Refusing unexpected Etsy image URL: {url}")

        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with self._open(url, image=True) as response:
                with tempfile.NamedTemporaryFile(
                    dir=path.parent, prefix=f".{path.name}.", delete=False
                ) as temp_file:
                    temp_path = Path(temp_file.name)
                    size = 0
                    while chunk := response.read(64 * 1024):
                        size += len(chunk)
                        if size > MAX_IMAGE_BYTES:
                            raise ValueError(
                                f"Image exceeds {MAX_IMAGE_BYTES} bytes: {url}"
                            )
                        temp_file.write(chunk)
            temp_path.replace(path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            raise ValueError(f"Invalid .env entry on line {line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if key.strip() in ENV_KEYS:
            values[key.strip()] = value
    return values


def _setting(name: str, env_file: dict[str, str]) -> str:
    return os.environ.get(name) or env_file.get(name, "")


def _iter_active_listings(api: EtsyAPI, shop_id: int):
    offset = 0
    limit = 100
    while True:
        page = api.get_json(
            f"/shops/{shop_id}/listings/active",
            {"limit": limit, "offset": offset},
        )
        results = page.get("results", []) or []
        if not results:
            return
        yield from results
        offset += len(results)
        total = page.get("count")
        if (total is not None and offset >= total) or len(results) < limit:
            return


def _featured_listing_order(api: EtsyAPI, shop_id: int) -> dict[int, int]:
    page = api.get_json(
        f"/shops/{shop_id}/listings/featured",
        {"limit": 20, "offset": 0},
    )
    return {
        int(listing["listing_id"]): rank
        for rank, listing in enumerate(page.get("results", []) or [])
        if listing.get("listing_id") is not None
    }


def _image_url(image: dict[str, Any]) -> str:
    return (
        image.get("url_570xN")
        or image.get("url_fullxfull")
        or image.get("url_170x135")
        or image.get("url_75x75")
        or ""
    )


def _image_extension(url: str) -> str:
    extension = Path(urlsplit(url).path).suffix.lower()
    return extension if extension in IMAGE_EXTENSIONS else ".jpg"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(value, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _prune_asset_images(assets_dir: Path, listings: list[dict[str, Any]]) -> None:
    active_listing_ids = {
        str(listing["listing_id"])
        for listing in listings
        if listing["listing_id"] is not None
    }
    kept_paths = {
        image["path"]
        for listing in listings
        for image in listing["images"]
    }

    if not assets_dir.exists():
        return

    for path in assets_dir.iterdir():
        if path.is_dir():
            if path.name not in active_listing_ids:
                shutil.rmtree(path)
                continue

            for image_path in path.rglob("*"):
                if not image_path.is_file():
                    continue
                relative_path = image_path.relative_to(assets_dir).as_posix()
                if relative_path not in kept_paths:
                    image_path.unlink()
            for directory in sorted(path.rglob("*"), reverse=True):
                if directory.is_dir():
                    if not any(directory.iterdir()):
                        directory.rmdir()
        elif path.is_file():
            path.unlink()


def sync_listings(
    api: EtsyAPI, shop_id: int, output: Path, assets_dir: Path
) -> list[dict[str, Any]]:
    listings = []
    featured_order = _featured_listing_order(api, shop_id)
    for summary in _iter_active_listings(api, shop_id):
        listing_id = int(summary["listing_id"])
        detail = api.get_json(
            f"/listings/{listing_id}", {"includes": "Images"}
        )
        raw_images = sorted(
            detail.get("images", []) or [],
            key=lambda image: int(image.get("rank", 0)),
        )
        images = []
        for image in raw_images[:1]:
            source_url = _image_url(image)
            if not source_url:
                continue
            rank = int(image.get("rank", len(images)))
            relative_path = Path(str(listing_id)) / f"image-{rank:02d}{_image_extension(source_url)}"
            api.download_image(source_url, assets_dir / relative_path)
            images.append(
                {
                    "path": relative_path.as_posix(),
                }
            )

        listings.append(
            {
                "listing_id": listing_id,
                "title": unescape(detail.get("title") or summary.get("title") or ""),
                "etsy_url": detail.get("url") or summary.get("url") or "",
                "section_id": detail.get("shop_section_id")
                or summary.get("shop_section_id"),
                "featured": listing_id in featured_order,
                "featured_order": featured_order.get(listing_id),
                "created_timestamp": detail.get("creation_timestamp"),
                "images": images,
            }
        )

    listings.sort(
        key=lambda listing: listing.get("created_timestamp") or 0, reverse=True
    )
    _write_json(output, listings)
    _prune_asset_images(assets_dir, listings)
    return listings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="dotenv-style file with Etsy credentials (default: .env)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/etsy/listings.json",
        help="Hugo data output path",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=ROOT / "assets/etsy",
        help="Directory for downloaded listing images",
    )
    args = parser.parse_args(argv)

    env_file = _read_env_file(args.env_file)
    api_key = _setting("ETSY_API_KEY", env_file)
    shared_secret = _setting("ETSY_SHARED_SECRET", env_file)
    shop_id = _setting("ETSY_OWN_SHOP_ID", env_file)
    if not api_key or not shared_secret or not shop_id:
        parser.error(
            "ETSY_API_KEY, ETSY_SHARED_SECRET, and ETSY_OWN_SHOP_ID must be set "
            "in the environment or --env-file"
        )
    try:
        listings = sync_listings(
            EtsyAPI(api_key, shared_secret),
            int(shop_id),
            args.output,
            args.assets_dir,
        )
    except (HTTPError, URLError, ValueError, KeyError) as error:
        print(f"Etsy sync failed: {error}", file=sys.stderr)
        return 1

    print(f"Synchronized {len(listings)} active Etsy listings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
