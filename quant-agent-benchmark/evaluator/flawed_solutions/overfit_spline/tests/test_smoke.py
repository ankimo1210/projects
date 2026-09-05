import unittest
from quantcurve.variant import VARIANT

class TestFixture(unittest.TestCase):
    def test_variant_exists(self):
        self.assertTrue(VARIANT)

if __name__ == "__main__":
    unittest.main()
