"""Illustrative agent model, not fitted to experiments or patient outcomes.

All numerical coefficients below are invented teaching parameters. One step is
one *model* day; distances are normalized to a 0..1 lesion. Separate random
streams per mechanism let paired runs share the same random draws.
"""
from dataclasses import asdict, dataclass, replace
import math
import random


@dataclass(frozen=True)
class Settings:
    scaffold: bool = True
    alignment: float = 0.85
    half_life: float = 42.0
    growth_factors: float = 0.65
    cells: float = 0.60
    scar: float = 0.55
    scar_modulation: float = 0.35
    gap: float = 1.0
    seed: int = 17
    axons: int = 60
    days: int = 84

    def __post_init__(self):
        for name in ('alignment', 'growth_factors', 'cells', 'scar', 'scar_modulation'):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'{name} must be between 0 and 1')
        if not math.isfinite(self.half_life) or not 1 <= self.half_life <= 200:
            raise ValueError('half_life must be between 1 and 200')
        if not math.isfinite(self.gap) or not 0.5 <= self.gap <= 2:
            raise ValueError('gap must be between 0.5 and 2')
        if not isinstance(self.seed, int) or not 0 <= self.seed <= 999999:
            raise ValueError('seed must be an integer between 0 and 999999')
        if not isinstance(self.axons, int) or not 1 <= self.axons <= 200:
            raise ValueError('axons must be an integer between 1 and 200')
        if not isinstance(self.days, int) or not 1 <= self.days <= 180:
            raise ValueError('days must be an integer between 1 and 180')


PRESETS = {
    'Combined approach': dict(scaffold=True, alignment=.85, half_life=42., growth_factors=.65, cells=.60, scar_modulation=.35),
    'Structure alone': dict(scaffold=True, alignment=.85, half_life=42., growth_factors=0., cells=0., scar_modulation=0.),
    'Bridge fades too soon': dict(scaffold=True, alignment=.85, half_life=7., growth_factors=.65, cells=.60, scar_modulation=.35),
    'Poorly aligned channels': dict(scaffold=True, alignment=.15, half_life=42., growth_factors=.65, cells=.60, scar_modulation=.35),
    'No scaffold': dict(scaffold=False, alignment=0., half_life=42., growth_factors=0., cells=0., scar_modulation=0.),
}


def scaffold_mass(day, cfg):
    return 2 ** (-day / cfg.half_life) if cfg.scaffold else 0.0


def growth_signal(day, cfg):
    """Transient local signal; exponential tail is a teaching assumption."""
    return cfg.growth_factors * math.exp(-day / 32) if cfg.scaffold else 0.0


def simulate(cfg: Settings):
    """Return JSON-safe trajectories, daily metrics, and explicit settings.

    'connected' means geometric target capture in the model, not a synapse,
    functional recovery, or an electrophysiological signal.
    """
    sources = [0.10 + 0.80 * i / max(1, cfg.axons - 1) for i in range(cfg.axons)]
    agents = [dict(x=0., y=y, state='growing', crossed=False) for y in sources]
    paths = [[[0., round(y, 5)]] for y in sources]
    # A fixed number of draws per axon per day makes comparisons reproducible.
    rng_turn = random.Random(cfg.seed * 13 + 1)
    rng_survival = random.Random(cfg.seed * 13 + 2)
    rng_growth = random.Random(cfg.seed * 13 + 3)
    rng_target = random.Random(cfg.seed * 13 + 4)
    speed = [0.72 + .56 * rng_growth.random() for _ in agents]
    history = []
    frames = []

    def record(day):
        counts = {name: sum(a['state'] == name for a in agents)
                  for name in ('growing', 'connected', 'misdirected', 'stopped')}
        crossed = sum(a['crossed'] for a in agents)
        record = dict(day=day, **counts, crossed=crossed,
                      scaffold_remaining=round(scaffold_mass(day, cfg), 5),
                      growth_signal=round(growth_signal(day, cfg), 5),
                      mean_progress=round(sum(min(1., a['x']) for a in agents) / cfg.axons, 5))
        history.append(record)
        frames.append([dict(x=round(a['x'], 5), y=round(a['y'], 5), state=a['state']) for a in agents])

    record(0)
    for day in range(1, cfg.days + 1):
        mass = scaffold_mass(day, cfg)
        signal = growth_signal(day, cfg)
        # Living graft support decays over time, independent of polymer mass.
        cell_support = cfg.cells * math.exp(-day / 90) if cfg.scaffold else 0.
        guidance = cfg.alignment * mass if cfg.scaffold else 0.
        scar = cfg.scar * (1 - .65 * cfg.scar_modulation * mass) if cfg.scaffold else cfg.scar
        for i, a in enumerate(agents):
            turn = rng_turn.gauss(0, 1)
            survival = rng_survival.random()
            growth_noise = rng_growth.random()
            capture = rng_target.random()
            if a['state'] != 'growing':
                paths[i].append([round(a['x'], 5), round(a['y'], 5)])
                continue
            edge = math.exp(-((a['x'] - .08) / .12) ** 2) + math.exp(-((a['x'] - .92) / .12) ** 2)
            stop_chance = (.004 + .010 * scar + .014 * scar * edge) / (1 + 1.6 * cell_support + .9 * signal)
            if survival < stop_chance:
                a['state'] = 'stopped'
            else:
                forward = .027 * speed[i] * (.55 + .65 * mass + .70 * signal + .40 * cell_support)
                forward *= (1 - .55 * scar) * (.85 + .30 * growth_noise) / cfg.gap
                # Aligned channels reduce wandering and restore toward the axon's lane.
                a['y'] += .034 * (1 - .82 * guidance) * turn + .13 * guidance * (sources[i] - a['y'])
                a['x'] = min(1., a['x'] + forward)
                if a['x'] >= 1:
                    a['crossed'] = True
                if a['y'] < .02 or a['y'] > .98:
                    a['y'] = max(.02, min(.98, a['y']))
                    a['state'] = 'misdirected'
                elif a['x'] >= 1:
                    correct_lane = abs(a['y'] - sources[i]) < .065
                    # Toy capture probability is not measured synaptic integration.
                    captured = capture < .45 + .30 * cell_support + .20 * guidance
                    a['state'] = 'connected' if correct_lane and captured else 'misdirected'
            paths[i].append([round(a['x'], 5), round(a['y'], 5)])
        record(day)
    return dict(settings=asdict(cfg), sources=sources, paths=paths, frames=frames, history=history)


def paired_runs(cfg):
    baseline = replace(cfg, scaffold=False, alignment=0., growth_factors=0., cells=0., scar_modulation=0.)
    return simulate(baseline), simulate(cfg)


def sensitivity(cfg, seeds=range(5)):
    """Stochastic variability of this toy model; never a clinical interval."""
    seeds = tuple(seeds)
    result = []
    for name, values in PRESETS.items():
        connected = []
        crossed = []
        for seed in seeds:
            run = simulate(replace(cfg, **values, seed=seed))
            connected.append(run['history'][-1]['connected'])
            crossed.append(run['history'][-1]['crossed'])
        n = len(connected)
        if not n:
            raise ValueError('At least one seed is required')
        result.append(dict(scenario=name, mean_connected=round(sum(connected)/n, 1),
                           min_connected=min(connected), max_connected=max(connected),
                           mean_crossed=round(sum(crossed)/n, 1), runs=n))
    return result
