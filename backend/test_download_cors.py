import unittest

from applications import create_app


class DownloadCorsTestCase(unittest.TestCase):
    def test_upload_download_route_allows_configured_frontend_origin(self):
        app = create_app("testing")
        response = app.test_client().get(
            "/_uploads/photos/res/missing.png",
            headers={"Origin": "http://127.0.0.1:4174"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "http://127.0.0.1:4174",
        )
        self.assertEqual(response.headers.get("Access-Control-Allow-Credentials"), "true")


if __name__ == "__main__":
    unittest.main()
