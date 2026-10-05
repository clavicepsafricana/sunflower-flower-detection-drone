import unittest
from evaluate import evaluate


class MatchingTests(unittest.TestCase):
    def test_duplicate_prediction_cannot_match_twice(self):
        result = evaluate(dict(sector='test', reference=[[0, 0]], predictions=[[0, 0], [.01, 0]]), .15)
        self.assertEqual((result['matched'], result['unmatched_predictions']), (1, 1))

    def test_maximum_cardinality(self):
        result = evaluate(dict(sector='test', reference=[[0, 0], [.2, 0]], predictions=[[.1, 0], [-.1, 0]]), .15)
        self.assertEqual(result['matched'], 2)

    def test_empty_predictions(self):
        result = evaluate(dict(sector='test', reference=[[0, 0]], predictions=[]), .15)
        self.assertEqual(result['missed'], 1)
        self.assertIsNone(result['precision'])

    def test_uncertain_exclusion(self):
        result = evaluate(dict(sector='test', reference=[], predictions=[[0, 0]], uncertain=[[0, 0]]), .15)
        self.assertEqual(result['ignored_predictions'], 1)


if __name__ == '__main__':
    unittest.main()
