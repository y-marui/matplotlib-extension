import unittest
from matplotlib_extension.label_string import LabelString

class TestLabelString(unittest.TestCase):
    def test_single_keyword(self):
        self.assertEqual(repr(LabelString("para")), r"$\parallel$")
        self.assertEqual(repr(LabelString("perp")), r"$\perp$")
        self.assertEqual(repr(LabelString("alpha")), r"$\alpha$")
        self.assertEqual(repr(LabelString("beta")), r"$\beta$")
        self.assertEqual(repr(LabelString("gamma")), r"$\gamma$")

    def test_multiple_keywords(self):
        self.assertEqual(repr(LabelString("para alpha")), r"$\parallel$ $\alpha$")
        self.assertEqual(repr(LabelString("beta gamma")), r"$\beta$ $\gamma$")

    def test_no_keywords(self):
        self.assertEqual(repr(LabelString("test string")), "test string")

    def test_mixed_keywords_and_text(self):
        self.assertEqual(repr(LabelString("alpha and beta")), r"$\alpha$ and $\beta$")
        self.assertEqual(repr(LabelString("gamma is not beta")), r"$\gamma$ is not $\beta$")

if __name__ == "__main__":
    unittest.main()