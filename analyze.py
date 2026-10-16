#!/usr/bin/env python3
"""Analyze a Poke Genie collection against PvPoke ranking CSVs.

Install: pip install pandas
Run: python analyze.py --genie data/pokegenie/poke_genie_export.csv --pvpoke-dir data/pvpoke --output results

Place PvPoke CSVs anywhere under --pvpoke-dir; filenames must include cp1500 or
cp2500 and a category name (overall/leads/closers/chargers/switches or
switchers/attackers/consistency). Example: cp1500_all_attackers_rankings.csv.
Results are estimates, not simulated performance of your specimen's exact IVs.
"""
import argparse
import re
from pathlib import Path
import pandas as pd
from team_builder import build_teams

CATEGORY_ALIASES = {'overall':'overall','leads':'leads','lead':'leads','closers':'closers','closer':'closers',
                    'chargers':'chargers','charger':'chargers','switches':'switchers','switchers':'switchers',
                    'switch':'switchers','attackers':'attackers','attacker':'attackers','consistency':'consistency'}
FORM_ALIASES = {'alola':'alolan','galar':'galarian','hisui':'hisuian','paldea':'paldean',
                'origin forme':'origin','altered forme':'altered','normal':'',
                'standard':'','average':'average'}
COLUMNS = ['League','Category','Position','Pokemon','Owned Pokemon','Collection Index','CP','IVs',
           'PvPoke Score','PvPoke Rank','IV Rank','IV Rank Percent','Combined Score','Affordability Score','Investment Score',
           'Form','Shadow Status','Dust Cost','Candy Cost','Ready As Is','Fast Move',
           'Charged Move 1','Charged Move 2','Current Fast Move','Current Charge Move 1','Current Charge Move 2']

def clean(v):
    if pd.isna(v): return ''
    return re.sub(r'\s+', ' ', str(v).strip()).casefold()

def normalize_form(form):
    s=clean(form)
    return FORM_ALIASES.get(s,s)

def label(name, form, shadow, gender=''):
    name=str(name).strip()
    form=normalize_form(form)
    suffix=[]
    if form: suffix.append(form)
    if clean(name) in ('indeedee','oinkologne') and clean(gender) in ('♀','female'):
        suffix.append('female')
    if clean(name) in ('indeedee','oinkologne') and clean(gender) in ('♂','male'):
        suffix.append('male')
    if shadow == 1: suffix.append('shadow')
    return clean(name),tuple(sorted(set(suffix)))

def pvp_key(name):
    words=re.findall(r'\(([^)]*)\)',str(name))
    base=re.sub(r'\s*\([^)]*\)','',str(name)).strip()
    return clean(base),tuple(sorted(normalize_form(x) for x in words if normalize_form(x)))

def parse_pct(s):
    if pd.isna(s): return float('nan')
    try: return float(str(s).replace('%','').strip())
    except ValueError: return float('nan')

def find_files(folder):
    found={}
    for path in sorted(folder.rglob('*.csv')):
        stem=path.stem.casefold()
        league='Great' if 'cp1500' in stem else 'Ultra' if 'cp2500' in stem else None
        if not league: continue
        tokens=re.split(r'[_\s-]+',stem)
        category=next((CATEGORY_ALIASES[t] for t in tokens if t in CATEGORY_ALIASES),None)
        if category:
            key=(league,category)
            if key in found: print(f'WARNING duplicate {key}: keeping {found[key]}, ignoring {path}')
            else: found[key]=path
    return found

def analyze(genie, pvp_files, meta_weight=.8, top=5, unique=True, investment_weight=.25):
    results=[]; unmatched=[]; summaries=[]
    for (league,category),path in sorted(pvp_files.items()):
        suffix='G' if league=='Great' else 'U'
        name_col=f'Name ({suffix})';form_col=f'Form ({suffix})';sha_col=f'Sha/Pur ({suffix})'
        pct_col=f'Rank % ({suffix})';rank_col=f'Rank # ({suffix})'
        dust_col=f'Dust Cost ({suffix})';candy_col=f'Candy Cost ({suffix})'
        pvp=pd.read_csv(path)
        if not {'Pokemon','Score'}.issubset(pvp.columns):
            print(f'WARNING skipping {path}: expected Pokemon and Score'); continue
        pvp=pvp.copy(); pvp['Match Key']=pvp['Pokemon'].apply(pvp_key)
        # Ranking files should contain one row per Pokemon. Keep highest score if duplicated.
        pvp=pvp.sort_values('Score',ascending=False).drop_duplicates('Match Key')
        pvp=pvp.sort_values('Score',ascending=False).reset_index(drop=True)
        bykey={r['Match Key']:(i+1,r) for i,(_,r) in enumerate(pvp.iterrows())}
        matched=0; misses={}
        for _,r in genie.iterrows():
            if pd.isna(r.get(name_col)) or pd.isna(r.get(rank_col)): continue
            target=str(r[name_col]).strip()
            shadow=r.get(sha_col)
            # Poké Genie 0=normal, 1=shadow, 2=purified; purified uses non-shadow PvPoke meta entry.
            shadow=int(shadow) if pd.notna(shadow) else 0
            key=label(target,r.get(form_col),shadow,r.get('Gender'))
            hit=bykey.get(key)
            if hit is None:
                misses[key]=misses.get(key,0)+1
                continue
            matched+=1
            rank_pvp,record=hit
            iv_pct=parse_pct(r.get(pct_col))
            if pd.isna(iv_pct):
                # Fallback for exports lacking percentile field.
                iv_pct=100*(1-(float(r[rank_col])-1)/4095)
            iv_pct=max(0,min(100,iv_pct))
            score=float(record['Score'])
            combined=meta_weight*score+(1-meta_weight)*iv_pct
            as_is=clean(r.get('Name'))==clean(target) and normalize_form(r.get('Form'))==normalize_form(r.get(form_col))
            ivs='/'.join('-' if pd.isna(r.get(col)) else str(int(r[col])) for col in ('Atk IV','Def IV','Sta IV'))
            results.append({'League':league,'Category':category.title(),'Position':None,
                'Pokemon':record['Pokemon'],'Owned Pokemon':r['Name'],'Collection Index':r['Index'],
                'CP':r['CP'],'IVs':ivs,'PvPoke Score':score,'PvPoke Rank':rank_pvp,
                'IV Rank':int(r[rank_col]),'IV Rank Percent':round(iv_pct,3),
                'Combined Score':round(combined,3),'Affordability Score':None,'Investment Score':None,'Form':r.get(form_col),'Shadow Status':
                'Shadow' if shadow==1 else 'Purified' if shadow==2 else 'Normal',
                'Dust Cost':r.get(dust_col),'Candy Cost':r.get(candy_col),
                'Ready As Is':'Yes' if as_is else 'Evolution or form change needed',
                'Fast Move':record.get('Fast Move',''),'Charged Move 1':record.get('Charged Move 1',''),
                'Charged Move 2':record.get('Charged Move 2',''),
                'Current Fast Move':r.get('Quick Move'),'Current Charge Move 1':r.get('Charge Move'),
                'Current Charge Move 2':r.get('Charge Move 2')})
        summaries.append({'League':league,'Category':category,'PvPoke Entries':len(pvp),
                          'Matched Specimens':matched,'Unmatched Eligible Specimens':sum(misses.values()),'Source':path.name})
        for k,count in misses.items(): unmatched.append({'League':league,'Category':category,'Name':k[0],
                                               'Form/Status':', '.join(k[1]),'Count':count})
    all_rows=pd.DataFrame(results,columns=COLUMNS)
    if len(all_rows):
        # Percentile-based costs relative to the same league/category. Lower is better.
        # Missing cost data receives a neutral 50, not an artificial zero-cost advantage.
        # Costs supplied by Poké Genie do not necessarily cover second-move unlocks or TMs.
        def to_numeric_cost(series):
            return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False), errors='coerce')
        for cost_col, component_weight in [('Dust Cost', .7), ('Candy Cost', .3)]:
            costs=to_numeric_cost(all_rows[cost_col])
            # Values are independent across groups, so compare each species against its league/category.
            percentile=costs.groupby([all_rows['League'],all_rows['Category']]).rank(pct=True, ascending=True)
            affordability=(100*(1-percentile)).fillna(50)
            if cost_col=='Dust Cost': all_rows['Affordability Score']=component_weight*affordability
            else: all_rows['Affordability Score']+=component_weight*affordability
        all_rows['Affordability Score']=all_rows['Affordability Score'].round(3)
        all_rows['Investment Score']=((1-investment_weight)*all_rows['Combined Score']+investment_weight*all_rows['Affordability Score']).round(3)
        all_rows=all_rows.sort_values(['League','Category','Combined Score','PvPoke Score','IV Rank'],ascending=[True,True,False,False,True])
        all_rows['Position']=all_rows.groupby(['League','Category']).cumcount()+1
    best=all_rows.copy()
    if unique and len(best):
        # Best owned specimen per PvPoke species, per league/category.
        best=best.drop_duplicates(['League','Category','Pokemon']).copy()
        best['Position']=best.groupby(['League','Category']).cumcount()+1
    top5=best[best['Position']<=top].copy()
    investment=all_rows.sort_values(['League','Category','Investment Score','Combined Score','IV Rank'],ascending=[True,True,False,False,True]).copy()
    if unique and len(investment):
        investment=investment.drop_duplicates(['League','Category','Pokemon'])
    if len(investment):
        investment['Position']=investment.groupby(['League','Category']).cumcount()+1
    investment_top=investment[investment['Position']<=top].copy()
    return all_rows,best,top5,investment,investment_top,pd.DataFrame(summaries),pd.DataFrame(unmatched)

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--genie',type=Path,required=True)
    parser.add_argument('--pvpoke-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('results'))
    parser.add_argument('--meta-weight',type=float,default=.80,help='0 to 1; default 0.80')
    parser.add_argument('--top',type=int,default=5)
    parser.add_argument('--investment-weight',type=float,default=.25,help='Affordability contribution to investment ranking, 0 to 1 (default .25)')
    parser.add_argument('--team-candidates',type=int,default=45,help='Strongest candidate species considered per league (default 45)')
    parser.add_argument('--team-top',type=int,default=5,help='Number of teams per league (default 5)')
    parser.add_argument('--team-weights',type=float,nargs=4,metavar=('PERFORMANCE','DEFENSE','OFFENSE','INVESTMENT'),default=[40,25,20,15],help='Relative team priorities, default 40 25 20 15')
    parser.add_argument('--move-types',type=Path,help='Optional CSV mapping Move,Type for additional moves')
    parser.add_argument('--allow-duplicates',action='store_true',help='Show multiple specimens of same species in top five')
    args=parser.parse_args()
    if not 0<=args.meta_weight<=1: parser.error('--meta-weight must be 0..1')
    if not 0<=args.investment_weight<=1: parser.error('--investment-weight must be 0..1')
    if args.top<1: parser.error('--top must be at least 1')
    if args.team_top<1 or args.team_candidates<3: parser.error('--team-top must be >=1 and --team-candidates >=3')
    if any(v<0 for v in args.team_weights) or sum(args.team_weights)<=0: parser.error('--team-weights must be nonnegative, and not all zero')
    genie=pd.read_csv(args.genie)
    files=find_files(args.pvpoke_dir)
    if not files: parser.error('No ranking files found. Expected filenames including cp1500/cp2500 and category.')
    args.output.mkdir(parents=True,exist_ok=True)
    all_rows,best,top5,investment,investment_top,summary,unmatched=analyze(genie,files,args.meta_weight,args.top,not args.allow_duplicates,args.investment_weight)
    for name,frame in [('all_matches',all_rows),('best_by_species',best),('top_five',top5),('investment_by_species',investment),('top_five_investment',investment_top),('summary',summary),('unmatched',unmatched)]:
        frame.to_csv(args.output/f'{name}.csv',index=False)
    teams,team_notes=build_teams(all_rows,files,max_candidates=args.team_candidates,nteams=args.team_top,weights=args.team_weights,move_types=args.move_types)
    teams.to_csv(args.output/'top_teams.csv',index=False)
    team_notes.to_csv(args.output/'team_diagnostics.csv',index=False)
    if len(teams):
        print('\nRecommended teams (heuristic; not simulated PvPoke matchups):')
        print(teams[['League','Position','Lead','Switch','Closer','Team Score','Shared Weaknesses','Total Dust','Total Candy']].to_string(index=False))
    else: print('NOTE: No teams produced. See team_diagnostics.csv for reasons.')
    print(f'Analyzed {len(files)} PvPoke files; {len(genie)} owned Pokemon; {len(all_rows)} matched specimens across categories.')
    print(f'Outputs: {args.output.resolve()}')
    if len(investment_top): print('\nTop investment value:'); print(investment_top[['League','Category','Position','Pokemon','Investment Score','Affordability Score','Combined Score','Dust Cost','Candy Cost']].to_string(index=False))
    if len(top5): print('\nTop competitive potential:'); print(top5[['League','Category','Position','Pokemon','Combined Score','PvPoke Score','IV Rank']].to_string(index=False))
    if len(files)<14: print(f'NOTE: {len(files)}/14 category files supplied; add others and rerun.')

if __name__=='__main__':main()
