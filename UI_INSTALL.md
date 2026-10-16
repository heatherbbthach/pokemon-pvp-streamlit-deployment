# Pokédex-style interface update

This package contains **only** `app.py`, `.streamlit/config.toml`, and `requirements.txt` plus this note. It contains no personal Pokémon collection, PvPoke CSVs, or image assets.

## Update your GitHub repository

1. Replace the repository's root `app.py` with this `app.py`.
2. Replace `.streamlit/config.toml` with the included theme file (preserving the `.streamlit` folder).
3. Replace `requirements.txt` so Pillow is installed on Streamlit Cloud.
4. Keep your current `analyze.py`, `team_builder.py`, existing CSVs, and `assets/` folder **as they are**.
5. Commit and allow Streamlit Community Cloud to redeploy.

## Image paths

- `assets/logo.jpg`: centered, fitted inside 350 x 450 px without stretching or upscaling.
- `assets/greatleague.jpg`: above Great League results, fitted within 275 x 200 px.
- `assets/ultraleague.jpg`: above Ultra League results, fitted within 275 x 200 px.
- `assets/pokemon/<name-or-form>.png`: each Pokémon's artwork, fitted within 175 x 175 px. Supports PNG, WEBP, JPG, and JPEG. Missing art falls back to a placeholder; it does not break analysis.

The app continues to look for rankings at `data/pvpoke/` or `examples/sample_data/pvpoke/`. Users still upload their Poké Genie CSV in the browser. No changes to GitHub Actions or the data files are required.

## Preserved language

All of your upload guidance, October 15, 2026 PvPoke notice, priority descriptions, advanced settings, diagnostics, and download wording remain in place; the two text typos have been corrected.

## Important

Pokémon artwork must be placed in `assets/pokemon/` in the deployed repository. Some unusual form filenames may not match automatically: the app will display a placeholder rather than the wrong form. For example, both `giratina-altered.png` and `aegislash-shield.png` are recognized.
