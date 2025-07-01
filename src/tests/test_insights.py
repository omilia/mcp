import unittest
from unittest.mock import patch
from src.ocp.insights import InsightsClient

class TestConvertToMs(unittest.TestCase):
    def setUp(self):
        self.client = InsightsClient()

    def test_convert_to_ms_various(self):
        cases = [
            ("2024-07-01T12:00:00Z", "1719835200000"),  
            ("1720132800000", "1720132800000"),         
            (1720132800000, 1720132800000),             
            ("2024-07-01T12:00:00+00:00", "1719835200000"),
            ("2024-07-01T12:00:00+03:00", "1719824400000"),
            ("2024-07-01", "1719781200000"),  
            ("2024-07-01+00:00", "1719781200000"),
            ("2024-07-01+03:00", "1719792000000"),
        ]
        for input_val, expected in cases:
            with self.subTest(input_val=input_val):
                result = self.client._convert_to_ms(input_val)
                self.assertEqual(result, expected)

    def test_convert_to_ms_invalid(self):
        # Should return input if not a string or not a valid ISO
        self.assertIsNone(self.client._convert_to_ms(None))
        self.assertEqual(self.client._convert_to_ms(123), 123)
        # Should raise ValueError for invalid ISO string
        with self.assertRaises(ValueError):
            self.client._convert_to_ms("not-a-date")

class TestInsightsClientConstructor(unittest.TestCase):
    @patch("src.ocp.base.Authentication")
    def test_base_url_replacement(self, MockAuth):
        # Test mapped host
        mock_auth_instance = MockAuth.return_value
        mock_auth_instance.host = "https://us1-m.ocp.ai"
        client = InsightsClient()
        self.assertEqual(client.base_url, "https://us1-a.ocp.ai")

        # Test non-mapped host
        mock_auth_instance.host = "https://custom.ocp.ai"
        client = InsightsClient()
        self.assertEqual(client.base_url, "https://custom.ocp.ai")

if __name__ == "__main__":
    unittest.main() 