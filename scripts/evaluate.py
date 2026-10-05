"""Evaluate exported local-metre point samples; no QGIS required."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


def evaluate(sample, tolerance):
    def points(key):
        return np.asarray(sample.get(key, []), dtype=float).reshape(-1, 2)
    refs, predictions, uncertain = points('reference'), points('predictions'), points('uncertain')
    distances = cdist(refs, predictions)
    # Penalty exceeds any possible sum of valid distances: maximize cardinality first.
    penalty = (min(len(refs), len(predictions)) + 1) * (tolerance + 1)
    rows, cols = linear_sum_assignment(np.where(distances <= tolerance, distances, penalty))
    pairs = [(int(i), int(j)) for i, j in zip(rows, cols) if distances[i, j] <= tolerance]
    matched = {j for _, j in pairs}
    ignored = {j for j in range(len(predictions)) if j not in matched and len(uncertain)
               and cdist(predictions[j:j+1], uncertain).min() <= tolerance}
    tp = len(pairs)
    fp = len(predictions) - tp - len(ignored)
    return dict(sector=sample['sector'], reference=len(refs), predictions=len(predictions),
                matched=tp, unmatched_predictions=fp, missed=len(refs)-tp,
                uncertain=len(uncertain), ignored_predictions=len(ignored),
                precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/len(refs) if len(refs) else None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('samples', type=Path)
    parser.add_argument('--tolerance', type=float, default=0.15)
    parser.add_argument('--output', type=Path, default=Path('evaluation.json'))
    args = parser.parse_args()
    if args.tolerance <= 0:
        parser.error('tolerance must be positive (metres)')
    data = json.loads(args.samples.read_text(encoding='utf-8'))
    results = [evaluate(s, args.tolerance) for s in data['samples']]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'tolerance_m': args.tolerance, 'results': results}, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
