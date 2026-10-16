# Pokémon GO PvP Team Builder

A web-based tool that helps Pokémon GO players build competitive Great League and Ultra League teams using Pokémon they already own.

The Team Builder combines personal collection data from **Poké Genie** with competitive rankings from **PvPoke** to identify promising Pokémon, evaluate team synergy, and recommend balanced three-Pokémon teams.

Rather than simply recommending the highest-ranked Pokémon, the tool considers how well Pokémon work together, including their battle roles, offensive and defensive type coverage, individual IV quality, and the resources required to prepare them for battle.

## Features

### Personalized Pokémon Rankings

Upload a Poké Genie CSV export to evaluate your collection against PvPoke rankings.

The analyzer considers:

- Competitive performance based on PvPoke rankings
- Individual Pokémon PvP IV rankings
- Great League (1,500 CP) and Ultra League (2,500 CP) eligibility
- Battle roles, including leads, safe switches, and closers
- Estimated stardust and candy investment requirements

When you own multiple Pokémon of the same species, results include identifying information such as current CP, IVs, and collection index to help you locate the recommended specimen.

### Team Recommendations

The Team Builder recommends up to five three-Pokémon teams per league.

Each recommendation considers:

- **Competitive performance:** How strongly the Pokémon perform according to PvPoke.
- **Defensive coverage:** How effectively teammates resist or compensate for one another's type weaknesses.
- **Offensive coverage:** How effectively the team's recommended moves threaten opposing Pokémon types.
- **Investment efficiency:** How much stardust and candy are required to prepare the team.

The algorithm also evaluates shared weaknesses, complementary typing, and the suitability of Pokémon for different battle roles.

### Customizable Priorities

Not every player has the same priorities. Some want the strongest possible team, while others prefer affordable options or broader type coverage.

Use the four adjustable sliders to customize how heavily each factor influences your team recommendations.

Default weighting:

| Factor | Weight |
|---|---:|
| Competitive performance | 40% |
| Defensive coverage | 25% |
| Offensive coverage | 20% |
| Investment efficiency | 15% |

Weights are automatically normalized during analysis.

### Updated PvPoke Rankings

The application supports CSV exports from PvPoke for seven ranking categories:

- Overall
- Leads
- Closers
- Switches
- Chargers
- Attackers
- Consistency

Rankings are supported for both Great League and Ultra League.

When default ranking datasets are available, you can use them without uploading additional files. You can also upload more recent PvPoke CSVs to override the corresponding rankings for your analysis.

## How to Use

1. **Export your Pokémon collection:** Generate a CSV export of your collection using Poké Genie.
2. **Upload your collection:** Select your Poké Genie CSV in the application.
3. **Update rankings (optional):** Upload newer PvPoke ranking CSVs if you want to use different or more recent rankings.
4. **Customize your priorities:** Adjust the competitive performance, defensive coverage, offensive coverage, and investment efficiency sliders.
5. **Analyze your collection:** Select **Analyze my collection** to generate personalized recommendations.
6. **Explore your results:** Review recommended teams, individual Pokémon rankings, type coverage, IVs, current CPs, investment estimates, and diagnostics.
7. **Download your reports:** Export the results as a ZIP containing CSV reports.

## How Recommendations Are Calculated

The Team Builder uses a weighted scoring algorithm combining competitive rankings, individual Pokémon characteristics, type effectiveness, and investment costs.

It evaluates both offensive and defensive team synergy, rewarding complementary coverage and penalizing combinations with significant shared weaknesses.

The application uses heuristic scoring rather than direct battle simulations. Consequently, its scores represent comparative recommendations, not predicted win rates.

Actual battle performance also depends on movesets, shield management, energy management, opponent selection, and changes in the competitive meta.

## Data Privacy

Your Poké Genie CSV is uploaded for analysis and processed on the application hosting infrastructure.

The application does not intentionally store uploaded collections in a permanent database or commit them to GitHub. Temporary files may be used during processing, and generated results may remain available during your active session.

Uploaded information is processed on the hosting service rather than exclusively on your device.

## Run Locally

This project is written in Python and uses Streamlit for its web interface.

To run the application locally:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The interface will open in your browser, typically at `http://localhost:8501`.

## Limitations and Future Development

The Team Builder is an evolving project. Current limitations include:

- Rankings depend on the available PvPoke datasets and their competitive format.
- The algorithm evaluates typing and recommended moves but does not perform complete battle simulations.
- Some moves or forms may require additional mappings.
- Investment estimates may not capture every in-game resource requirement.
- Recommended teams should be evaluated alongside personal playstyle and current competitive conditions.

Potential future improvements include simulated matchup analysis, interactive type-coverage visualizations, more detailed investment comparisons, and additional league support.

## Acknowledgments

This project uses data exported from two independently developed Pokémon GO resources:

- **[Poké Genie](https://www.pokegenie.net/)** — Pokémon collection analysis and individual PvP IV rankings.
- **[PvPoke](https://pvpoke.com/)** — Competitive Pokémon rankings, moveset recommendations, and battle analysis.

Poké Genie and PvPoke are independent third-party tools. This project is not affiliated with or endorsed by either service, Niantic, or The Pokémon Company.

Pokémon and Pokémon GO are trademarks of their respective owners.
