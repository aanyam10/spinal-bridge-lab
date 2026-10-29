"""Model invariants and reproducibility, not a claim of biological validation."""
from dataclasses import replace
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import Settings, growth_signal, paired_runs, scaffold_mass, sensitivity, simulate


class ModelTests(unittest.TestCase):
    def test_deterministic_seed(self):
        cfg = Settings(axons=12, days=20)
        self.assertEqual(simulate(cfg), simulate(cfg))
        self.assertNotEqual(simulate(cfg)['paths'], simulate(replace(cfg, seed=18))['paths'])

    def test_counts_and_trajectories(self):
        # Include boundary slider settings, not only the default case.
        for cfg in (Settings(), Settings(alignment=0, half_life=7, scar=1, gap=2),
                    Settings(alignment=1, scar=0, gap=.5, cells=1, growth_factors=1)):
            run = simulate(cfg)
            self.assertEqual(len(run['history']), cfg.days + 1)
            self.assertEqual(len(run['frames']), cfg.days + 1)
            for path in run['paths']:
                self.assertEqual(len(path), cfg.days + 1)
                self.assertTrue(all(0 <= x <= 1 and 0 <= y <= 1 for x, y in path))
                self.assertTrue(all(path[i+1][0] >= path[i][0] for i in range(cfg.days)))
            for row, frame in zip(run['history'], run['frames']):
                self.assertEqual(sum(row[s] for s in ('growing','stopped','misdirected','connected')), cfg.axons)
                self.assertLessEqual(row['connected'], row['crossed'])
                self.assertLessEqual(row['crossed'], cfg.axons)
                self.assertEqual(row['crossed'], sum(a['x'] == 1 for a in frame))
            for prev, curr in zip(run['history'], run['history'][1:]):
                self.assertGreaterEqual(curr['crossed'], prev['crossed'])
                self.assertGreaterEqual(curr['connected'], prev['connected'])
                self.assertLessEqual(curr['scaffold_remaining'], prev['scaffold_remaining'])

    def test_no_scaffold_ignores_scaffold_controls(self):
        a, b = paired_runs(Settings(scaffold=False, alignment=1, cells=1, growth_factors=1, scar_modulation=1))
        self.assertEqual(a['paths'], b['paths'])
        self.assertEqual(a['history'], b['history'])
        self.assertTrue(all(r['scaffold_remaining'] == r['growth_signal'] == 0 for r in b['history']))

    def test_no_scaffold_baseline_keeps_injury(self):
        cfg = Settings(scar=.8, gap=1.7, seed=77)
        a, b = paired_runs(cfg)
        for key in ('scar', 'gap', 'seed', 'days', 'axons'):
            self.assertEqual(a['settings'][key], b['settings'][key])
        self.assertEqual(a['sources'], b['sources'])

    def test_half_life_and_signal(self):
        cfg=Settings(half_life=42)
        self.assertAlmostEqual(scaffold_mass(42,cfg), .5)
        self.assertAlmostEqual(scaffold_mass(84,cfg), .25)
        self.assertLess(growth_signal(20,cfg), growth_signal(0,cfg))

    def test_comparison_consumes_generator_once(self):
        rows = sensitivity(Settings(axons=4,days=3), (i for i in range(2)))
        self.assertEqual(len(rows),5)
        self.assertTrue(all(r['runs']==2 for r in rows))
        with self.assertRaises(ValueError):
            sensitivity(Settings(), [])

    def test_invalid_inputs(self):
        for kwargs in ({'alignment':1.1},{'gap':0},{'half_life':0},{'scar':math.nan},
                       {'cells':-1},{'axons':0},{'days':1000},{'seed':-1}):
            with self.assertRaises(ValueError):
                Settings(**kwargs)

    def test_stopped_paths_remain_stopped(self):
        run=simulate(Settings())
        for i in range(60):
            states=[f[i]['state'] for f in run['frames']]
            for t,state in enumerate(states):
                if state != 'growing':
                    self.assertTrue(all(s==state for s in states[t:]))
                    self.assertTrue(all(p==run['paths'][i][t] for p in run['paths'][i][t:]))
                    break


if __name__ == '__main__':
    unittest.main()
