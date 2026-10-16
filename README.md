# Pokémon GO PvP Team Builder — Streamlit web app

A browser interface to analyze a Pokémon GO collection against PvPoke rankings and recommend teams with configurable competitive, defensive, offensive, and investment priorities.

## Run on your own computer

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Host with Streamlit Community Cloud

1. Put **only the application files** in a GitHub repository; do **not** commit your Poké Genie collection. Do not upload the sample/example Poké Genie CSV from previous project archives either.
2. Optionally copy your current PvPoke ranking CSVs into `data/pvpoke/` so visitors don't have to upload all the rankings. Verify that you have permission to redistribute any third-party datasets you publish. If you omit those files, each visitor can upload PvPoke CSVs via the browser.
3. Visit https://share.streamlit.io, sign in with GitHub, choose **Create app**, point to the repository and `app.py`, then click Deploy.
4. In Streamlit app settings, change **Sharing → Who can view this app** to **This app is public and searchable** (particularly important if the GitHub repository is private).
5. Test from a private browser window with a real Poké Genie CSV and the PvPoke data source of your choice.

### Visitor workflow

- Upload Poké Genie CSV from the web interface.
- Optionally upload newer PvPoke ranking CSVs (filenames like `cp1500_all_leads_rankings.csv`). Uploaded category rankings override bundled ones for that run.
- Adjust the four priority sliders and select **Analyze my collection**.
- View teams, CPs, ranks, diagnostics; download a results ZIP.

### Privacy and limitations

The app uses in-memory uploads and temporary working directories for downloaded rankings. A visitor's CSV is processed **on Streamlit's hosting infrastructure**, not exclusively in their browser. This code does not intentionally persist uploaded collections to disk, GitHub, or a database; however, Streamlit session state keeps generated reports for the active session. The hosting platform may process operational logs/telemetry under its own policies. Do not claim files never leave the user's device.

The Team Builder uses heuristics, **not simulated win rates**; its move type mapping is finite. Report any missing type/move mappings.

**Do not deploy the existing private working repository publicly while it still tracks your personal Poké Genie collection.** This deploy bundle excludes it and can be used as the basis of a separate deployment repository. A `.gitignore` does not untrack previously committed files.

See [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
