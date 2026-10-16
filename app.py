"""Streamlit front end to the Pokémon GO PvP roster analyzer."""
from __future__ import annotations

import io
import re
import unicodedata
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from analyze import analyze, find_files
from team_builder import build_teams

ROOT = Path(__file__).resolve().parent
CATEGORIES = ['overall','leads','closers','chargers','switchers','attackers','consistency']
REPORTS = ('all_matches','best_by_species','top_five','investment_by_species',
           'top_five_investment','summary','unmatched','top_teams','team_diagnostics')


def default_data():
    """Use whichever of the supported existing repository layouts is present."""
    for dirname in ('data/pvpoke', 'examples/sample_data/pvpoke'):
        folder = ROOT / dirname
        if folder.exists() and find_files(folder):
            return folder
    return None


def zip_reports(frames):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as out:
        for name, df in frames.items():
            out.writestr(f'{name}.csv', df.to_csv(index=False))
    return buffer.getvalue()


def generate(genie_bytes, bundled_dir, updates, weights, meta_weight, investment_weight, top, candidates):
    with tempfile.TemporaryDirectory(prefix='pokemon-pvp-') as scratch:
        folder = Path(scratch)
        genie = pd.read_csv(io.BytesIO(genie_bytes))
        if not len(genie):
            raise ValueError('The Poké Genie CSV has no rows.')
        paths = {}
        if bundled_dir is not None:
            paths.update(find_files(bundled_dir))
        # uploaded file names must identify league and category; this same matcher is used by the CLI
        for i, (filename, data) in enumerate(updates):
            dest = folder / f'{i}' / Path(filename).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            mapped = find_files(dest.parent)
            if len(mapped) != 1:
                raise ValueError(f'Cannot identify league and category from {filename}. Example: cp1500_all_leads_rankings.csv')
            key = next(iter(mapped))
            # Ensure correct PvPoke schema before replacing an existing valid file.
            header = pd.read_csv(dest, nrows=0).columns
            if not {'Pokemon','Score'}.issubset(header):
                raise ValueError(f'{filename} needs Pokemon and Score columns.')
            paths[key] = dest
        if not paths:
            raise ValueError('No PvPoke rankings found. Add CSVs named with cp1500/cp2500 and the ranking category.')
        all_rows, best, top5, investment, investment_top, summary, unmatched = analyze(
            genie, paths, meta_weight=meta_weight, top=top, unique=True,
            investment_weight=investment_weight)
        teams, diagnostics = build_teams(all_rows, paths, max_candidates=candidates,
                                          nteams=top, weights=weights)
        frames = dict(zip(REPORTS, (all_rows,best,top5,investment,investment_top,
                                    summary,unmatched,teams,diagnostics)))
        return frames, sorted(f'{k[0]} / {k[1]}' for k in paths), len(genie)


ASSETS = ROOT / 'assets'
POKEMON_IMAGES = ASSETS / 'pokemon'

# Exact-form artwork is preferred; never silently show a different form when a
# form-specific image is missing.
IMAGE_ALIASES = {
    'giratina altered': 'giratina-altered',
    'giratina origin': 'giratina-origin',
    'aegislash shield': 'aegislash-shield',
    'aegislash blade': 'aegislash-blade',
    'pumpkaboo': 'pumpkaboo-average',
    'alolan sandslash': 'sandslash-alola',
    'alolan sandshrew': 'sandshrew-alola',
    'galarian stunfisk': 'stunfisk-galar',
}


def image_slug(name):
    """Normalize species and form labels into filenames such as giratina-altered."""
    label = str(name).strip().lower().replace('♀', '-f').replace('♂', '-m')
    label = re.sub(r'\bshadow\b', '', label).strip()
    label = label.replace('(', ' ').replace(')', ' ')
    label = unicodedata.normalize('NFKD', label)
    label = ''.join(c for c in label if not unicodedata.combining(c))
    label = re.sub(r'[^a-z0-9]+', '-', label).strip('-')
    return label


def pokemon_image(name):
    key = image_slug(name)
    stem = IMAGE_ALIASES.get(key.replace('-', ' '), key)
    candidates = [stem]
    # Alternative regional form conventions from popular image datasets.
    for region in ('alolan', 'galarian', 'hisuian', 'paldean'):
        if key.startswith(region + '-'):
            base = key[len(region)+1:]
            candidates.extend([f'{base}-{region}', f'{base}-{region[:-2] if region.endswith("ian") else region}'])
    for candidate in dict.fromkeys(candidates):
        for extension in ('.png', '.webp', '.jpg', '.jpeg'):
            path = POKEMON_IMAGES / f'{candidate}{extension}'
            if path.is_file():
                return path
    return None


def scaled_image(filename, maximum_width, maximum_height):
    """Scale down to fit within maximum dimensions; never distort or upscale."""
    file = ROOT / filename
    if not file.is_file():
        return False
    try:
        with Image.open(file) as opened:
            picture = opened.copy()
        picture.thumbnail((maximum_width, maximum_height), Image.Resampling.LANCZOS)
        st.image(picture)
        return True
    except (OSError, ValueError):
        return False


def image_centered(path, maximum_width, maximum_height):
    left, middle, right = st.columns([1, 2, 1])
    with middle:
        return scaled_image(path, maximum_width, maximum_height)


def pretty_value(value):
    if pd.isna(value) or str(value).strip() == '':
        return '—'
    if isinstance(value, (int, float)):
        return f'{value:,.0f}'
    return str(value)


def render_member(record, role):
    name = str(record.get(role, 'Unknown Pokémon'))
    with st.container(border=True):
        st.markdown(f'<div class="role-label">{role if role != "Switch" else "Safe Switch"}</div>', unsafe_allow_html=True)
        artwork = pokemon_image(name)
        if artwork:
            scaled_image(str(artwork.relative_to(ROOT)), 175, 175)
        else:
            st.markdown('<div class="missing-art">◉</div>', unsafe_allow_html=True)
        st.markdown(f'**{name}**')
        typing = record.get(f'{role} Typing', '')
        if pd.notna(typing) and str(typing).strip():
            st.caption(str(typing).replace('/', ' / '))
        st.markdown(f'**Current CP:** {pretty_value(record.get(f"{role} Current CP"))}')
        st.caption(f'IV rank: {pretty_value(record.get(f"{role} IV Rank"))}')
        st.caption(f'IVs: {pretty_value(record.get(f"{role} IVs"))}')
        st.caption(f'Collection index: {pretty_value(record.get(f"{role} Collection Index"))}')
        original = record.get(f'{role} Owned Pokemon')
        if pd.notna(original) and str(original).strip() and str(original) != name:
            st.caption(f'Owned as: {original}')


st.set_page_config(page_title='Pokémon GO PvP Team Builder', page_icon='⚔️', layout='wide')
st.markdown("""
<style>
:root { --pokedex-red:#E84646; --pokedex-yellow:#F7C948; --pokedex-blue:#58B8E8; --pokedex-green:#77C9A4; }
.block-container { max-width: 1300px; padding-top: 2rem; }
h1,h2,h3 { letter-spacing: -.02em; }
h1 { color: #F7C948 !important; }
h2 { color: #58B8E8 !important; padding-top: .7rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
[data-testid="stFileUploader"] { background: #363B46; border-radius: 14px; padding: .5rem 1rem; }
[data-testid="stButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"] {
    background: #F7C948; color: #252830; border: 0; font-weight: 800; border-radius: 12px;
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stDownloadButton"] button[kind="primary"]:hover { background:#ffe07d; color:#252830; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#F7C948; }
.role-label { display:inline-block; background:#E84646; color:white; padding:5px 12px;
  border-radius:20px; font-size:.82rem; font-weight:800; margin-bottom:8px; }
.missing-art { height:160px; display:flex; align-items:center; justify-content:center;
  color:#58B8E8; font-size:76px; background:#252830; border-radius:12px; }
.team-eyebrow { color:#77C9A4; font-size:.83rem; font-weight:750; letter-spacing:.07em; text-transform:uppercase; }
</style>
""", unsafe_allow_html=True)

image_centered('assets/logo.jpg', 350, 450)
st.title('⚔️ Pokémon GO PvP Team Builder')
st.write('Find your best competitive Pokémon and build complementary teams using **your collection**, PvPoke rankings, and your priorities. All calculations run in this app session.')

st.header('1 · Your Poké Genie export')
genie_file = st.file_uploader('Upload your Poké Genie collection CSV', type=['csv'], key='genie',
                              help='Export your scanned collection from Poké Genie as CSV.')

st.header('2 · PvPoke rankings')
st.caption('This tool automatically checks against PvPoke CSV exports from 10/15/2026. If you wish to use more recent exports, please upload them.')
default = default_data()
if default:
    existing = find_files(default)
    st.success(f'Found {len(existing)} bundled league/category rankings. Upload your own if you would like to use more recent rankings.')
else:
    existing = {}
    st.info('No bundled rankings found. Please upload PvPoke ranking CSVs below.')
st.caption('New uploads override matching bundled categories **for this analysis only**.')
replace = st.file_uploader('Optional: upload newer PvPoke CSVs (multiple allowed)',
                            type=['csv'], accept_multiple_files=True, key='pvpoke')

st.header('3 · Team-building priorities')
st.caption('Please select how important each of the following is to you for your team composition. They will be normalized automatically to total 100%.')
c1,c2 = st.columns(2)
with c1:
    performance = st.slider('Competitive performance',0,100,40,5)
    defense = st.slider('Defensive type coverage',0,100,25,5)
with c2:
    offense = st.slider('Offensive move coverage',0,100,20,5)
    investment = st.slider('Investment efficiency',0,100,15,5)
weights = [performance, defense, offense, investment]
if sum(weights):
    normalized = [100*x/sum(weights) for x in weights]
    st.write('Effective weighting: ' + ' · '.join(f'{key}: **{value:.1f}%**' for key,value in zip(
        ('Performance','Defense','Offense','Investment'), normalized)))
else:
    st.warning('Select a nonzero value for at least one priority.')

with st.expander('Advanced settings'):
    meta = st.slider('PvPoke importance in individual competitive score (%)', 0,100,80)
    affordable = st.slider('Affordability importance in individual investment score (%)',0,100,25)
    count = st.number_input('Recommended teams per league', min_value=1,max_value=25,value=5)
    candidates = st.number_input('Candidate Pokémon considered per league',min_value=3,max_value=120,value=45)

if st.button('Analyze my collection',type='primary',disabled=(not genie_file or not sum(weights))):
    try:
        with st.spinner('Matching Pokémon and building teams...'):
            frames, available, n_owned = generate(
                genie_file.getvalue(), default,
                [(f.name, f.getvalue()) for f in replace], weights,meta/100,affordable/100,
                int(count),int(candidates))
            st.session_state['reports'] = frames
            st.session_state['source_count'] = len(available)
            st.session_state['owned_count'] = n_owned
        st.success(f'Analyzed {n_owned} Pokémon using {len(available)} PvPoke ranking files.')
    except Exception as exc:
        st.error(f'Analysis could not finish: {exc}')
        st.info('Check the Poké Genie export format and PvPoke CSV filenames and columns.')

if 'reports' in st.session_state:
    frames = st.session_state['reports']
    st.header('Your results')
    teams = frames['top_teams']
    tab_teams,tab_rankings,tab_diagnostics = st.tabs(['Recommended teams','Individual rankings','Diagnostics'])
    with tab_teams:
        if teams.empty:
            st.warning('No teams generated. See Diagnostics for why (for example missing Pokémon type columns).')
        else:
            leagues = sorted(teams['League'].dropna().unique())
            league = st.selectbox('League', leagues, key='league')
            selected = teams[teams['League']==league]
            league_name = str(league).lower()
            if '1500' in league_name or 'great' in league_name:
                image_centered('assets/greatleague.jpg', 275, 200)
                st.subheader('Great League Teams')
            elif '2500' in league_name or 'ultra' in league_name:
                image_centered('assets/ultraleague.jpg', 275, 200)
                st.subheader('Ultra League Teams')
            for index, (_, team) in enumerate(selected.iterrows(), start=1):
                with st.container(border=True):
                    st.markdown(f'<div class="team-eyebrow">Recommended Team {index}</div>', unsafe_allow_html=True)
                    cols = st.columns(3)
                    for col, role in zip(cols, ('Lead', 'Switch', 'Closer')):
                        with col:
                            render_member(team, role)
                    score, dust, candy = st.columns(3)
                    score.metric('Team score', f"{float(team['Team Score']):.2f}" if pd.notna(team.get('Team Score')) else '—')
                    dust.metric('Estimated stardust', pretty_value(team.get('Total Dust')))
                    candy.metric('Estimated candy', pretty_value(team.get('Total Candy')))
                    weaknesses = team.get('Shared Weaknesses', '')
                    if pd.notna(weaknesses) and str(weaknesses).strip():
                        st.caption(f'Shared weaknesses: {weaknesses}')
            with st.expander('All team statistics and specimen identifiers'):
                st.dataframe(selected,hide_index=True,use_container_width=True)
    with tab_rankings:
        st.dataframe(frames['top_five'],hide_index=True,use_container_width=True)
        st.markdown('**Top investment candidates**')
        st.dataframe(frames['top_five_investment'],hide_index=True,use_container_width=True)
    with tab_diagnostics:
        st.dataframe(frames['team_diagnostics'],hide_index=True,use_container_width=True)
        st.markdown('**Files processed**')
        st.dataframe(frames['summary'],hide_index=True,use_container_width=True)
    st.download_button('Download all reports as ZIP',zip_reports(frames),
                       file_name='pokemon-pvp-results.zip',mime='application/zip',type='primary')
    st.caption('Team scores are ranking heuristics, not simulated win rates. Investment costs may omit second-move unlocks and TMs.')
