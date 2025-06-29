import unittest
from src.ocp.insights import InsightsClient

class TestConvertToMs(unittest.TestCase):
    def setUp(self):
        self.client = InsightsClient()

    def test_convert_to_ms_various(self):
        cases = [
            ("2024-07-01T12:00:00Z", "1719835200000"),  # ISO string UTC
            ("1720132800000", "1720132800000"),         # Already ms string
            (1720132800000, 1720132800000),               # Already ms int
            ("2024-07-01T12:00:00+00:00", "1719835200000"), # ISO with explicit offset
            ("2024-07-01T12:00:00+03:00", "1719824400000"), # ISO with +03:00 offset
            # Extra test cases for ISO dates without time
            ("2024-07-01", "1719781200000"),  # Date only, assumed midnight UTC
            ("2024-07-01+00:00", "1719781200000"),  # Date only with offset
            ("2024-07-01+03:00", "1719792000000"),  # Date only with +03:00 offset
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

if __name__ == "__main__":
    unittest.main() 