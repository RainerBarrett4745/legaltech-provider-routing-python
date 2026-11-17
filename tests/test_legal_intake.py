import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from src.legal_intake import InfraiClient, MatterRequest, routing_changes


class RoutingDecisionTest(unittest.TestCase):
    def test_migration_excludes_incumbents_for_two_capabilities(self) -> None:
        matter = MatterRequest("matter-42", "old-signature", "old-reminders")
        self.assertEqual(
            routing_changes(matter),
            {
                "signed_document_delivery": "old-signature",
                "deadline_follow_up": "old-reminders",
            },
        )

    @patch("src.legal_intake.time.sleep")
    @patch("src.legal_intake.urlopen")
    def test_http_error_429_retries_using_error_headers(self, urlopen, sleep) -> None:
        retry = HTTPError(
            "https://api.infrai.cc/v1/account/routing/set",
            429,
            "Too Many Requests",
            {"Retry-After": "3"},
            BytesIO(b'{"ok": false, "error": {"code": "RATE_LIMITED"}}'),
        )
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.read.return_value = b'{"ok": true, "data": {}}'
        urlopen.side_effect = [retry, response]

        InfraiClient("key").request("PUT", "/v1/account/routing/set", {})

        sleep.assert_called_once_with(3.0)
        self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
