import unittest
from truth import Verifier

class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = Verifier()

    def test_verify(self):
        result = self.verifier.verify("The Earth is round.")
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()