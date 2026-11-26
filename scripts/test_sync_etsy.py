import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from sync_etsy import EtsyAPI, _image_extension, _read_env_file, sync_listings


class EtsySyncTests(unittest.TestCase):
    def test_reads_dotenv_values_without_shell_expansion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "ETSY_API_KEY='key with spaces'\n"
                "ETSY_SHARED_SECRET=secret # comment\n"
                "ETSY_OWN_SHOP_ID=$NOT_EXPANDED\n"
                "ANTHROPIC_API_KEY=must-not-be-loaded\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _read_env_file(path),
                {
                    "ETSY_API_KEY": "key with spaces",
                    "ETSY_SHARED_SECRET": "secret",
                    "ETSY_OWN_SHOP_ID": "$NOT_EXPANDED",
                },
            )

    def test_image_extension_uses_known_formats_only(self):
        self.assertEqual(_image_extension("https://i.etsystatic.com/1/2.png"), ".png")
        self.assertEqual(_image_extension("https://i.etsystatic.com/1/2.unknown"), ".jpg")

    def test_image_request_headers_do_not_include_api_credentials(self):
        api = EtsyAPI("api-key", "shared-secret")
        response = Mock()
        response.headers = {}
        with patch("sync_etsy.urlopen", return_value=response) as mocked_urlopen:
            api._open("https://i.etsystatic.com/41/cover.jpg", image=True)

        request = mocked_urlopen.call_args.args[0]
        self.assertNotIn("X-api-key", request.headers)

    def test_sync_writes_sorted_active_listings_and_image_metadata(self):
        api = Mock()
        api.get_json.side_effect = [
            {"count": 1, "results": [{"listing_id": 41}]},
            {
                "count": 1,
                "results": [{"listing_id": 41, "title": "That&#39;s It | More details", "url": "https://etsy.test/41"}],
            },
            {
                "listing_id": 41,
                "title": "That&#39;s It | More details",
                "url": "https://etsy.test/41",
                "shop_section_id": 8,
                "creation_timestamp": 1700000000,
                "images": [
                    {
                        "rank": 1,
                        "url_fullxfull": "https://i.etsystatic.com/41/cover.jpg",
                    },
                    {
                        "rank": 2,
                        "url_fullxfull": "https://i.etsystatic.com/41/alternate.jpg",
                    },
                ],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / "assets/41/image-01.jpg"
            stale_image_path = root / "assets/41/image-02.jpg"
            stale_listing_path = root / "assets/99/image-01.jpg"
            stale_image_path.parent.mkdir(parents=True)
            stale_image_path.write_bytes(b"stale")
            stale_listing_path.parent.mkdir(parents=True)
            stale_listing_path.write_bytes(b"stale")

            def download_image(url, path):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"image")

            api.download_image.side_effect = download_image
            output = root / "data/listings.json"
            listings = sync_listings(api, 42, output, root / "assets")

            self.assertEqual(len(listings), 1)
            self.assertEqual(listings[0]["title"], "That's It | More details")
            self.assertEqual(listings[0]["section_id"], 8)
            self.assertTrue(listings[0]["featured"])
            self.assertEqual(listings[0]["featured_order"], 0)
            self.assertEqual(len(listings[0]["images"]), 1)
            self.assertEqual(listings[0]["images"][0]["path"], "41/image-01.jpg")
            self.assertNotIn("price", listings[0])
            self.assertNotIn("description", listings[0])
            self.assertNotIn("updated_timestamp", listings[0])
            self.assertNotIn("alt", listings[0]["images"][0])
            self.assertTrue(image_path.exists())
            self.assertFalse(stale_image_path.exists())
            self.assertFalse(stale_listing_path.exists())
            api.download_image.assert_called_once_with(
                "https://i.etsystatic.com/41/cover.jpg",
                root / "assets/41/image-01.jpg",
            )
            api.get_json.assert_any_call(
                "/shops/42/listings/featured", {"limit": 20, "offset": 0}
            )
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), listings)


if __name__ == "__main__":
    unittest.main()
