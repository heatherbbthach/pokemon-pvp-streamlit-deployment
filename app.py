"""Streamlit front end to the Pokémon GO PvP roster analyzer."""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

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


st.set_page_config(page_title='Pokémon GO PvP Team Builder', page_icon='⚔️', layout='wide')
st.title('⚔️ Pokémon GO PvP Team Builder')
st.write('Find your best competitive Pokémon and build complementary teams using **your collection**, PvPoke rankings, and your priorities. All calculations run in this app session.')

st.header('1 · Your Poké Genie export')
genie_file = st.file_uploader('Upload your Poké Genie collection CSV', type=['csv'], key='genie',
                              help='Export your scanned collection from Poké Genie as CSV.')

st.header('2 · PvPoke rankings')
default = default_data()
if default:
    existing = find_files(default)
    st.success(f'Found {len(existing)} bundled league/category rankings in `{default.relative_to(ROOT)}`.')
else:
    existing = {}
    st.info('No bundled rankings found. Please upload PvPoke ranking CSVs below.')
st.caption('New uploads override matching bundled categories **for this analysis only**. Other bundled categories remain available. Nothing is changed in your repository.')
replace = st.file_uploader('Optional: upload newer PvPoke CSVs (multiple allowed)',
                            type=['csv'], accept_multiple_files=True, key='pvpoke')

st.header('3 · Team-building priorities')
st.caption('These are relative importance values, not probabilities. They will be normalized automatically to total 100%.')
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
            league = st.selectbox('League',sorted(teams['League'].dropna().unique()),key='league')
            filtered=teams[teams['League']==league]
            prominent=['Position','Lead','Lead Current CP','Switch','Switch Current CP',
                       'Closer','Closer Current CP','Team Score','Shared Weaknesses',
                       'Total Dust','Total Candy']
            st.dataframe(filtered[[c for c in prominent if c in filtered.columns]],
                         hide_index=True,use_container_width=True)
            with st.expander('All team statistics and specimen identifiers'):
                st.dataframe(filtered,hide_index=True,use_container_width=True)
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
