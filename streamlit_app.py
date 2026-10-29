"""Streamlit entry point for Spinal Bridge Lab."""
from dataclasses import asdict
import csv
import io
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from model import PRESETS, Settings, paired_runs, sensitivity

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title='Spinal Bridge Lab · Aanya Mendapara', layout='wide')
st.markdown('''<style>
.stApp{background:#fafaf5;color:#253334}
.block-container{max-width:1200px;padding-top:2rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#eef2eb;border-right:1px solid #dce4d9}
h1{font-family:Georgia,serif!important;font-weight:400!important;letter-spacing:-2px!important;font-size:3.3rem!important;line-height:1.06!important;padding:8px 0!important}
h2,h3{letter-spacing:-.5px}.eyebrow{font-size:11px;font-weight:700;letter-spacing:2px;color:#147d70;margin:0 0 6px}.dek{font-size:17px;line-height:1.65;color:#62716e;max-width:700px;margin:9px 0 18px}.hero{padding-bottom:10px}.stTabs [data-baseweb="tab-list"]{gap:28px;border-bottom:1px solid #dde5df}.stTabs [data-baseweb="tab"]{height:48px;padding-left:0;padding-right:0}.stTabs [aria-selected="true"]{color:#147d70!important}.stButton>button{border-radius:9px}.stMetric{border:1px solid #dde5df;background:#fff;border-radius:12px;padding:12px}
[data-testid="stSidebar"] h2{font-size:1.2rem}[data-testid="stSidebar"] label{font-size:13px}
.context{border-left:3px solid #a9c9b1;padding:12px 18px;background:#f0f5ed;border-radius:0 12px 12px 0;color:#4f635a;font-size:14px;margin:12px 0 20px}.footer{font-size:11px;color:#7c8c82;border-top:1px solid #dce4d9;margin-top:22px;padding-top:15px}.mini{font-size:12px;color:#66776f}
@media(max-width:700px){h1{font-size:2.5rem!important}.block-container{padding-top:1.3rem;padding-left:1rem;padding-right:1rem}.dek{font-size:15px}.stTabs [data-baseweb="tab-list"]{gap:16px}}
</style>''', unsafe_allow_html=True)

defaults = asdict(Settings())
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def apply_preset():
    for key, value in PRESETS[st.session_state['preset']].items():
        st.session_state[key] = value


with st.sidebar:
    st.markdown('<div class="eyebrow">DESIGN YOUR BRIDGE</div>', unsafe_allow_html=True)
    st.header('Small changes.\nDifferent paths.')
    st.caption('Choose a starting point, then change one variable at a time.')
    st.selectbox('Starting scenario', list(PRESETS), key='preset', on_change=apply_preset,
                 help='Loading a scenario resets scaffold settings. Injury conditions stay the same.')
    st.toggle('Add a scaffold', key='scaffold')
    off = not st.session_state['scaffold']
    st.slider('Channel alignment', 0., 1., step=.05, key='alignment', disabled=off,
              help='0 = little directional guidance; 1 = strongly aligned channels. A model parameter, not a measured score.')
    st.slider('Scaffold half-life (model days)', 7., 84., step=7., key='half_life', disabled=off,
              help='The time for half the scaffold to disappear. Exponential degradation is an illustrative assumption.')
    st.slider('Local growth-factor support', 0., 1., step=.05, key='growth_factors', disabled=off,
              help='Relative signal strength, not a clinical dose. The signal declines with time.')
    st.slider('Neural cell support', 0., 1., step=.05, key='cells', disabled=off,
              help='An abstract survival and growth benefit. This is not a number of cells or a model of graft safety.')
    st.slider('Scar modulation', 0., 1., step=.05, key='scar_modulation', disabled=off,
              help='Reduces part of the modeled growth barrier. Does not remove the entire scar.')
    st.divider()
    st.markdown('**The injury environment**')
    st.slider('Scar inhibition', 0., 1., step=.05, key='scar',
              help='Relative growth-inhibiting environment. The protective role of the scar is explained in the article.')
    st.slider('Relative gap length', .5, 2., step=.1, key='gap',
              help='1× is the default model gap, with no millimetre or human anatomical equivalent.')
    with st.expander('Reproducibility'):
        st.number_input('Random seed', min_value=0, max_value=999999, step=1, key='seed')
        st.caption('Same seed + same settings = same paths. Both panels share random draws. Each run starts with 60 model axons.')
    st.caption('Illustrative model · no patient data')

cfg = Settings(**{k: st.session_state[k] for k in defaults})


@st.cache_data(show_spinner=False, max_entries=32)
def calculate(settings):
    return paired_runs(Settings(**settings))


@st.cache_data(show_spinner=False, max_entries=16)
def calculate_variability(settings):
    return sensitivity(Settings(**settings))


baseline, design = calculate(asdict(cfg))

st.markdown(f'''<div class="hero"><div class="eyebrow">REGENERATIVE MEDICINE · AN INTERACTIVE EXPLORATION</div>
<h1>What if repair<br>had a pathway?</h1>
<div class="dek">Build a temporary bridge across an injured spinal cord.<br>Explore what helps axons grow, and what it takes to find their way.</div>
</div>''', unsafe_allow_html=True)

simulation, = st.tabs(['Explore the Simulation'])

with simulation:
    data = json.dumps(dict(baseline=baseline, design=design), separators=(',', ':'), allow_nan=False)
    html = (ROOT / 'frontend.html').read_text(encoding='utf-8').replace('__SIMULATION_DATA__', data)
    components.html(html, height=1020, scrolling=True)
    st.markdown('### Keep exploring')
    st.markdown('Try **Structure alone**, then **Combined approach** with the same injury and seed. Next try **Bridge fades too soon**. Which paths cross the gap, and which reach their assigned target?')
    with st.expander('Compare five scenarios across five random seeds'):
        st.caption('Final model-day results at your current scar inhibition and gap length. Presets use their own scaffold settings. Ranges show randomness inside this model, not scientific confidence intervals or evidence of treatment efficacy.')
        if st.button('Run scenario comparison'):
            rows = calculate_variability(asdict(cfg))
            st.dataframe([{
                'Scenario': r['scenario'], 'Mean across gap (of 60)': r['mean_crossed'],
                'Mean target matches (of 60)': r['mean_connected'],
                'Target matches: min–max': f"{r['min_connected']}–{r['max_connected']}",
                'Seeds': '0, 1, 2, 3, 4'
            } for r in rows], hide_index=True, use_container_width=True)
    stream = io.StringIO()
    fields = ['scenario', *design['history'][0].keys()]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for name, run in [('without_scaffold', baseline), ('your_design', design)]:
        writer.writerows(dict(scenario=name, **row) for row in run['history'])
    c1, c2 = st.columns(2)
    c1.download_button('↓ Download daily results (CSV)', stream.getvalue(), 'spinal_bridge_results.csv', 'text/csv', use_container_width=True)
    export = dict(model_version='1.0.0', purpose='Illustrative teaching model; not clinically validated',
                  settings=asdict(cfg), baseline_final=baseline['history'][-1], design_final=design['history'][-1])
    c2.download_button('↓ Download settings (JSON)', json.dumps(export, indent=2), 'spinal_bridge_settings.json', 'application/json', use_container_width=True)

st.markdown('<div class="footer">SPINAL BRIDGE LAB · Built for Aanya Mendapara’s exploration of regenerative medicine · Educational simulation · No patient data collected</div>', unsafe_allow_html=True)
