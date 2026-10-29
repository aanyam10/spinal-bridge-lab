# Spinal Bridge Lab

An interactive educational simulation by Aanya Mendapara. Design a temporary
scaffold and watch 60 model axons attempt to cross a spinal cord injury gap.

**Live app:** https://spinalcordbridge.streamlit.app/

## Explore

Change channel alignment, scaffold half-life, growth-factor support, neural
cell support, scar modulation, scar inhibition, and relative gap length.
Compare identical injury conditions with and without a scaffold. Play or scrub
the 84-model-day timeline, compare five scenarios across seeds 0–4, and download
daily results as CSV or settings and summaries as JSON.

The app contains only **Explore the Simulation**, with no article link.
Changing a setting restarts the timeline. Presets retain the injury conditions
and seed. Turning the scaffold off ignores all scaffold support controls.

## Run locally without extra installations

With Python 3.12, run from this folder:

```bash
python3 local_app.py
```

Open http://localhost:8501. Stop with Control+C. For another port, run
`python3 local_app.py --port 8502`. The local preview uses the same model and
animation as the hosted app. On macOS, `zsh Start-Local.command` also starts it.

## Run with Streamlit

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

No API keys, database, patient data, or external JavaScript libraries are used.
Streamlit Community Cloud deploys `streamlit_app.py` from the `main` branch.

## Scientific scope and assumptions

This is an **illustrative two-dimensional stochastic agent model**, not a
validated model of spinal cord regeneration, patient recovery, or treatment
efficacy. Numerical coefficients are invented teaching parameters, not fitted
to experiments. Preset rankings follow those assumptions.

Distance is normalized with no millimetre equivalent. One step is one model
day, not a calibrated biological day. A target match means arriving within
0.065 lateral units of an assigned lane and passing a toy random capture
check. It does not establish a real synapse, useful electrical signaling, or
functional recovery. Crossing the gap and matching a target are distinct.

Scaffold mass follows `M(t) = 2^(-t / half_life)`. Growth signal and cell support
decay as `G0 * exp(-t / 32)` and `C0 * exp(-t / 90)`. Alignment reduces lateral
wandering and guides paths toward their lanes. Scar inhibition slows movement
and increases stopping risk. See `model.py` for every coefficient.

The model omits 3D anatomy, real injury dimensions, blood supply, detailed
immune biology, graft safety, neural relays, remyelination, real synapses,
rehabilitation, and long-term material effects. It cannot establish an optimal
scaffold, dose, or treatment. Ranges across seeds are model variation, not
clinical confidence intervals.

## Verification

```bash
python3 -m unittest discover -s tests -v
```

Eight tests cover reproducibility, paired baseline conditions, trajectory and
count invariants, scaffold-off behavior, decay arithmetic, terminal states,
input validation, and scenario comparison. GitHub Actions runs them on pushes
and pull requests. These tests verify software behavior, not biology.

## Research informing the concepts

- Koffler et al. (2019): https://doi.org/10.1038/s41591-018-0296-z
- Nekanti et al. (2024): https://doi.org/10.1038/s41536-024-00356-0
- Álvarez et al. (2021): https://doi.org/10.1126/science.abh3602
- Harrop et al. (2025), INSPIRE 2.0: https://pubmed.ncbi.nlm.nih.gov/39471088/

These sources motivate the concepts; they do not validate the simulation's
coefficients, counts, or treatment comparisons.
