"""Rank complementary three-Pokémon GO PvP teams using owned specimens.

Transparent heuristic, NOT a PvPoke team simulation. The type chart models attack
multipliers, while PvPoke scores estimate performance by role. Unknown move types
receive no offensive-coverage credit and are reported in diagnostics.
"""
from __future__ import annotations

import itertools
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

TYPES = ('normal','fire','water','electric','grass','ice','fighting','poison','ground',
         'flying','psychic','bug','rock','ghost','dragon','dark','steel','fairy')
# Super-effective, resisted and immune defending types, per attacking type.
CHART = {
 'normal': ((), ('rock','steel'), ('ghost',)),
 'fire': (('grass','ice','bug','steel'),('fire','water','rock','dragon'),()),
 'water': (('fire','ground','rock'),('water','grass','dragon'),()),
 'electric': (('water','flying'),('electric','grass','dragon'),('ground',)),
 'grass': (('water','ground','rock'),('fire','grass','poison','flying','bug','dragon','steel'),()),
 'ice': (('grass','ground','flying','dragon'),('fire','water','ice','steel'),()),
 'fighting': (('normal','ice','rock','dark','steel'),('poison','flying','psychic','bug','fairy'),('ghost',)),
 'poison': (('grass','fairy'),('poison','ground','rock','ghost'),('steel',)),
 'ground': (('fire','electric','poison','rock','steel'),('grass','bug'),('flying',)),
 'flying': (('grass','fighting','bug'),('electric','rock','steel'),()),
 'psychic': (('fighting','poison'),('psychic','steel'),('dark',)),
 'bug': (('grass','psychic','dark'),('fire','fighting','poison','flying','ghost','steel','fairy'),()),
 'rock': (('fire','ice','flying','bug'),('fighting','ground','steel'),()),
 'ghost': (('psychic','ghost'),('dark',),('normal',)),
 'dragon': (('dragon',),('steel',),('fairy',)),
 'dark': (('psychic','ghost'),('fighting','dark','fairy'),()),
 'steel': (('ice','rock','fairy'),('fire','water','electric','steel'),()),
 'fairy': (('fighting','dragon','dark'),('fire','poison','steel'),()),
}
# Common Pokémon GO move names. Users can extend or override with --move-types.
# Use pipe-delimited strings to retain multiword move names.
MOVE_GROUPS = {
 'normal':'Tackle|Quick Attack|Scratch|Pound|Body Slam|Hyper Beam|Return|Frustration|Swift|Wrap|Slam|Stomp|Take Down|Headbutt|Horn Attack|Tri Attack|Boomburst|Last Resort|Lock On|Yawn|Cut|Present|Struggle|Normal Weather Ball',
 'fire':'Fire Spin|Fire Fang|Ember|Incinerate|Fire Blast|Flamethrower|Fire Punch|Blast Burn|Overheat|Flame Charge|Flame Wheel|Heat Wave|Fireball|Sacred Fire|Fusion Flare|Mystical Fire|Torch Song|Blaze Kick|Weather Ball Fire|Fire Weather Ball|V-create|Lava Plume|Magma Storm|Burn Up',
 'water':'Water Gun|Waterfall|Bubble|Splash|Hydro Pump|Hydro Cannon|Aqua Tail|Aqua Jet|Surf|Scald|Water Pulse|Liquidation|Brine|Crabhammer|Razor Shell|Origin Pulse|Dive|Aqua Break|Weather Ball Water|Water Weather Ball|Muddy Water|Water Shuriken',
 'electric':'Thunder Shock|Volt Switch|Spark|Charge Beam|Thunderbolt|Thunder|Discharge|Wild Charge|Thunder Punch|Zap Cannon|Parabolic Charge|Fusion Bolt|Volt Tackle|Electro Ball|Thunder Fang|Electroweb|Supercell Slam|Nuzzle',
 'grass':'Vine Whip|Razor Leaf|Bullet Seed|Leaf Blade|Grass Knot|Power Whip|Solar Beam|Frenzy Plant|Seed Bomb|Energy Ball|Leaf Storm|Magical Leaf|Petal Blizzard|Trailblaze|Leaf Tornado|Grass Weather Ball|Weather Ball Grass|Giga Drain|Absorb',
 'ice':'Ice Shard|Powder Snow|Frost Breath|Ice Fang|Ice Beam|Ice Punch|Icy Wind|Blizzard|Avalanche|Icicle Spear|Triple Axel|Weather Ball Ice|Ice Weather Ball|Freeze-Dry|Aurora Beam|Glaciate',
 'fighting':'Counter|Karate Chop|Low Kick|Rock Smash|Double Kick|Force Palm|Close Combat|Cross Chop|Dynamic Punch|Focus Blast|Superpower|Power-Up Punch|Brick Break|Low Sweep|Flying Press|Aura Sphere|Sacred Sword|High Jump Kick|Drain Punch|Submission',
 'poison':'Poison Jab|Poison Sting|Acid|Poison Fang|Cross Poison|Sludge Bomb|Sludge Wave|Gunk Shot|Acid Spray|Sludge|Poison Tail|Venoshock|Poison Gas',
 'ground':'Mud Shot|Mud Slap|Mud Bomb|Earthquake|Earth Power|High Horsepower|Drill Run|Sand Tomb|Scorching Sands|Bulldoze|Dig|Precipice Blades|Stomping Tantrum|Bone Club',
 'flying':'Air Slash|Wing Attack|Peck|Gust|Hurricane|Sky Attack|Aerial Ace|Brave Bird|Fly|Air Cutter|Acrobatics|Drill Peck|Feather Dance|Oblivion Wing|Bleakwind Storm',
 'psychic':'Confusion|Psycho Cut|Extrasensory|Zen Headbutt|Psychic|Psybeam|Psyshock|Future Sight|Psystrike|Psychic Fangs|Synchronoise|Stored Power|Luster Purge|Mist Ball|Heart Stamp',
 'bug':'Bug Bite|Bug Buzz|Bug Pulse|Bug Attack|Infestation|Struggle Bug|Fury Cutter|X-Scissor|Signal Beam|Silver Wind|Fell Stinger|Lunge|Megahorn|Leech Life',
 'rock':'Rock Throw|Smack Down|Rock Slide|Stone Edge|Rock Blast|Rock Tomb|Ancient Power|Power Gem|Meteor Beam|Rock Wrecker|Rollout|Accelerock',
 'ghost':'Shadow Claw|Hex|Astonish|Lick|Shadow Ball|Shadow Punch|Shadow Sneak|Ominous Wind|Night Shade|Poltergeist|Shadow Force|Spirit Shackle|Spectral Thief',
 'dragon':'Dragon Breath|Dragon Tail|Dragon Claw|Dragon Pulse|Outrage|Draco Meteor|Breaking Swipe|Twister|Dragon Ascent|Roar of Time|Spacial Rend|Dragon Energy',
 'dark':'Snarl|Bite|Sucker Punch|Feint Attack|Crunch|Dark Pulse|Foul Play|Night Slash|Brutal Swing|Payback|Obstruct|Throat Chop|Darkest Lariat',
 'steel':'Metal Claw|Bullet Punch|Iron Tail|Steel Wing|Flash Cannon|Iron Head|Heavy Slam|Meteor Mash|Mirror Shot|Doom Desire|Double Iron Bash|Magnet Bomb|Gyro Ball|Sunsteel Strike|Gigaton Hammer|Steel Beam',
 'fairy':'Charm|Fairy Wind|Disarming Voice|Dazzling Gleam|Play Rough|Moonblast|Draining Kiss|Moonlight|Spirit Break|Nature’s Madness|Natures Madness|Misty Explosion',
}
MOVE_TYPES = {re.sub(r'[^a-z0-9]+','',name.casefold()):type_name
              for type_name, names in MOVE_GROUPS.items() for name in names.split('|')}


def type_multiplier(attack_type, defense_types):
    """Includes dual types, 4x weakness, .25x resistance, and immunity (.390625 in GO)."""
    se, resist, immune = CHART[attack_type]
    product = 1.0
    for typ in defense_types:
        if typ in immune: product *= 0.390625
        elif typ in se: product *= 1.6
        elif typ in resist: product *= .625
    return product


def load_move_types(path=None):
    mapping = dict(MOVE_TYPES)
    if path:
        frame = pd.read_csv(path)
        if not {'Move','Type'}.issubset(frame.columns):
            raise ValueError('Move type CSV must have Move and Type columns')
        for row in frame.itertuples(index=False):
            name = str(getattr(row,'Move')).strip()
            typ = str(getattr(row,'Type')).strip().lower()
            if typ not in TYPES: raise ValueError(f'Invalid move type {typ!r} for {name}')
            mapping[re.sub(r'[^a-z0-9]+','',name.casefold())] = typ
    return mapping


def move_type(name, mapping):
    if not isinstance(name, str) or not name.strip() or name.strip().lower() == 'nan': return None
    key = re.sub(r'[^a-z0-9]+','',name.replace('*','').casefold())
    return mapping.get(key)


def build_teams(all_rows, pvp_files, *, max_candidates=45, nteams=5,
                weights=(.4,.25,.2,.15), move_types=None):
    """Return (teams, diagnostics). Requires rankings containing Type 1/Type 2.

    Builds each team's lead/switch/closer from available role rankings; when role
    rankings aren't supplied, category performance is used as an explicit proxy.
    """
    if len(weights)!=4 or any(w<0 for w in weights) or sum(weights)<=0:
        raise ValueError('Need four nonnegative weights with a positive sum')
    weights = [w/sum(weights) for w in weights]
    mt = load_move_types(move_types)
    output=[]; diagnostics=[]
    if all_rows.empty: return pd.DataFrame(),pd.DataFrame()
    for league in ('Great','Ultra'):
        owned = all_rows[all_rows['League']==league].copy()
        if owned.empty: continue
        league_files = {cat:path for (lg,cat),path in pvp_files.items() if lg==league}
        if not league_files: continue
        roster = {}
        # Pull typing from *all* supplied PvPoke CSVs: each entry supplies typing.
        for cat,path in league_files.items():
            frame = pd.read_csv(path)
            if not {'Pokemon','Type 1','Type 2'}.issubset(frame.columns):
                diagnostics.append({'League':league,'Issue':'Missing type columns','Details':path.name})
                continue
            for _,row in frame.iterrows():
                pokemon=str(row['Pokemon'])
                typ=tuple(t for t in (str(row['Type 1']).strip().lower(),str(row['Type 2']).strip().lower()) if t in TYPES)
                if not typ: continue
                if pokemon not in roster: roster[pokemon]={'types':typ,'moves':[]}
                for col in ('Fast Move','Charged Move 1','Charged Move 2'):
                    m=row.get(col)
                    if pd.notna(m) and str(m).strip():
                        roster[pokemon]['moves'].append(str(m).strip())
        if not roster:
            diagnostics.append({'League':league,'Issue':'No usable PvPoke type data','Details':'Need Type 1 and Type 2 columns in ranking CSVs'})
            continue
        by_species=defaultdict(dict)
        for _,r in owned.iterrows():
            name=r['Pokemon']; cat=str(r['Category']).lower()
            if name not in roster: continue
            by_species[name][cat]=max(by_species[name].get(cat,0),float(r['Combined Score']))
        # Pick the highest competitive score per specimen, but retain role-specific
        # candidate records (and individual costs) for final team selection.
        by_specimen=defaultdict(list)
        for _,r in owned.iterrows():
            if r['Pokemon'] not in roster: continue
            index=str(r['Collection Index'])
            by_specimen[(index,r['Pokemon'])].append(r)
        candidates=[]
        for (index,name),rows in by_specimen.items():
            pick=max(rows,key=lambda r:float(r['Combined Score']))
            # Closest existing data for role. Unavailable categories are not silently
            # treated as real roles; diagnostic below communicates fallback.
            row_score={str(r['Category']).casefold():float(r['Combined Score']) for r in rows}
            fallback=row_score.get('overall',sum(row_score.values())/len(row_score))
            roles={role:row_score.get(role,fallback) for role in ('leads','switchers','closers')}
            types=roster[name]['types']
            resolved=set(); unknown=set()
            for m in roster[name]['moves']:
                typ=move_type(m,mt)
                if typ: resolved.add(typ)
                else: unknown.add(m)
            if unknown: diagnostics.append({'League':league,'Issue':'Unknown move types','Details':name+': '+', '.join(sorted(unknown))})
            candidates.append({'name':name,'index':index,'types':types,'moves':resolved,
                'score':fallback,'roles':roles,'cost':float(pick['Affordability Score']),
                'dust':pd.to_numeric(pick['Dust Cost'],errors='coerce'),
                'candy':pd.to_numeric(pick['Candy Cost'],errors='coerce'),
                'iv_rank':pick['IV Rank'],
                'current_cp':pd.to_numeric(pick.get('CP'),errors='coerce'),
                'owned_name':pick.get('Owned Pokemon',''),
                'ivs':pick.get('IVs','')})
        # Keep only strongest specimen per species (teams require distinct species).
        # Include the best lead/switch/closer candidates even if overall weaker.
        unique={}
        for c in candidates:
            merit=max([c['score'],*c['roles'].values()])
            if c['name'] not in unique or merit>max([unique[c['name']]['score'],*unique[c['name']]['roles'].values()]):
                unique[c['name']]=c
        candidates=list(unique.values())
        ordered=sorted(candidates,key=lambda c:max([c['score'],*c['roles'].values()]),reverse=True)
        pool=ordered[:max_candidates]
        for role in ('leads','switchers','closers'):
            for c in sorted(candidates,key=lambda x:x['roles'][role],reverse=True)[:max(5,max_candidates//6)]:
                if c not in pool: pool.append(c)
        if len(pool)<3:
            diagnostics.append({'League':league,'Issue':'Too few matched species','Details':f'{len(pool)} species; need at least three'})
            continue
        for role in ('leads','switchers','closers'):
            if role not in league_files:
                diagnostics.append({'League':league,'Issue':'Role ranking unavailable','Details':role+'; using overall/available score as fallback'})
        def defense(team):
            # Count overlapping offensive threats. Penalize types where multiple
            # team members are weak and nobody resists; reward resistive partners.
            vulnerabilities=[]; uncovered=[]; covered=[]
            for attack_type in TYPES:
                vals=[type_multiplier(attack_type,c['types']) for c in team]
                weak=sum(v>1.01 for v in vals); resistant=sum(v<.99 for v in vals)
                if weak>=2: vulnerabilities.append(attack_type)
                if weak and not resistant: uncovered.append(attack_type)
                if weak and resistant: covered.append(attack_type)
            raw=100 - 12*len(vulnerabilities) - 5*len(uncovered) + 2*len(covered)
            return max(0,min(100,raw)),vulnerabilities,uncovered,covered
        def offense(team):
            move_types=set().union(*(c['moves'] for c in team))
            if not move_types: return 0,[],[]
            hit=[typ for typ in TYPES if any(type_multiplier(move,(typ,))>1 for move in move_types)]
            # Move typing vs single-type targets is a coverage proxy, not meta winrate.
            return 100*len(hit)/len(TYPES),hit,sorted(move_types)
        all_options=[]
        for team in itertools.combinations(pool,3):
            identifiers=[c['index'] for c in team]
            if len(set(identifiers))<3: continue
            # Avoid mono-type trios; two shared typings may still be useful in a deliberate core.
            if set.intersection(*(set(c['types']) for c in team)): continue
            d_score,shared,uncovered,covered=defense(team)
            o_score,hits,move_types_used=offense(team)
            # six permutations select best lead/switch/closer assignment.
            assigned=max(itertools.permutations(team),key=lambda perm:
                         .4*perm[0]['roles']['leads']+.3*perm[1]['roles']['switchers']+.3*perm[2]['roles']['closers'])
            # Role-weighted performance considers the actual roles, not just species scores.
            perf=.4*assigned[0]['roles']['leads']+.3*assigned[1]['roles']['switchers']+.3*assigned[2]['roles']['closers']
            cost=sum(c['cost'] for c in team)/3
            # Explicit high penalty for triple-shared vulnerabilities.
            triple=sum(1 for t in TYPES if all(type_multiplier(t,c['types'])>1 for c in team))
            if triple: continue  # A single attack type threatens every member.
            score=sum(w*v for w,v in zip(weights,(perf,d_score,o_score,cost)))
            def cost_total(field):
                values=[c[field] for c in team]
                return int(sum(values)) if all(pd.notna(v) for v in values) else ''
            all_options.append({'League':league,'Team Score':round(score,2),
              'Lead':assigned[0]['name'],'Lead Collection Index':assigned[0]['index'],
              'Switch':assigned[1]['name'],'Switch Collection Index':assigned[1]['index'],
              'Closer':assigned[2]['name'],'Closer Collection Index':assigned[2]['index'],
              'Lead IV Rank':assigned[0]['iv_rank'],'Switch IV Rank':assigned[1]['iv_rank'],'Closer IV Rank':assigned[2]['iv_rank'],
              'Lead Current CP':assigned[0]['current_cp'],'Switch Current CP':assigned[1]['current_cp'],
              'Closer Current CP':assigned[2]['current_cp'],
              'Lead Owned Pokemon':assigned[0]['owned_name'],'Switch Owned Pokemon':assigned[1]['owned_name'],
              'Closer Owned Pokemon':assigned[2]['owned_name'],
              'Lead IVs':assigned[0]['ivs'],'Switch IVs':assigned[1]['ivs'],'Closer IVs':assigned[2]['ivs'],
              'Performance':round(perf,2),'Defense':round(d_score,2),'Offense':round(o_score,2),
              'Affordability':round(cost,2),'Total Dust':cost_total('dust'),'Total Candy':cost_total('candy'),
              'Shared Weaknesses':', '.join(shared) or 'None',
              'Uncovered Weaknesses':', '.join(uncovered) or 'None',
              'Covered Weaknesses':', '.join(covered) or 'None',
              'Move Type Coverage':', '.join(move_types_used) or 'Unknown',
              'Super-effective vs Types':', '.join(hits) or 'Unknown',
              'Lead Typing':'/'.join(assigned[0]['types']),'Switch Typing':'/'.join(assigned[1]['types']),
              'Closer Typing':'/'.join(assigned[2]['types']),
              '_team':frozenset(c['name'] for c in team)})
        # Diverse options: disallow same three species reordered.
        all_options.sort(key=lambda r:r['Team Score'],reverse=True)
        selected=[]; seen=set()
        for r in all_options:
            if r['_team'] in seen: continue
            seen.add(r['_team']); r.pop('_team');r['Position']=len(selected)+1
            selected.append(r)
            if len(selected)>=nteams: break
        output.extend(selected)
        diagnostics.append({'League':league,'Issue':'Analyzed candidates','Details':f'{len(pool)} species; {len(all_options)} candidate teams'})
    return pd.DataFrame(output),pd.DataFrame(diagnostics).drop_duplicates()
