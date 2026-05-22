"""Existing tests for utils.py."""
import unittest
from utils import validate_email, format_currency, truncate_string


class TestValidateEmail(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(validate_email("user@example.com"))

    def test_missing_at(self):
        self.assertFalse(validate_email("userexample.com"))

    def test_missing_domain(self):
        self.assertFalse(validate_email("user@"))

    def test_empty(self):
        self.assertFalse(validate_email(""))


class TestFormatCurrency(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(format_currency(10.50), "$10.50")

    def test_zero(self):
        self.assertEqual(format_currency(0), "$0.00")

    def test_none(self):
        self.assertEqual(format_currency(None), "$0.00")


class TestTruncateString(unittest.TestCase):
    def test_short(self):
        self.assertEqual(truncate_string("hi", 10), "hi")

    def test_long(self):
        self.assertEqual(truncate_string("hello world", 5), "hello...")

    def test_empty(self):
        self.assertEqual(truncate_string("", 5), "")

    def test_exact(self):
        self.assertEqual(truncate_string("hello", 5), "hello")