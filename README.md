# Fresh Pending vs Flow Study

Does the Arabica coffee newly presented for ICE grading ("fresh pending") follow the green coffee shipped from each origin, and does that pipeline move the KC 1/2 spread?

Three markets (sidebar switch): **Belgium** (Antwerp grading vs flows to Belgium), **US** (Houston, Miami, New Orleans, New York, Virginia vs flows to the US) and **BE + US** (both, flows summed). The US is a consumer market, so only a few % of its imports get graded and fits are weaker.

## Folders

| Folder | Purpose |
|---|---|
| Code | `build_db.py`: reads the local source projects and writes the study database (no API calls, a few seconds) |
| Database | `grading_daily.parquet`, `flows_monthly.parquet`, `spread_daily.parquet`, `fits.parquet` (precomputed lead-lag), `manifest.json` (committed for Streamlit Cloud); `Logs/` not in git |
| Dashboard | Streamlit app: `app.py`, `core.py` (data and maths), `theme.py` (SnD look), `views/` (one file per section) |
| Automator | `run_update.bat`: build, then commit and push the Database files if they changed |

## Sources (local copies, each refreshed by its own automator)

| Data | From | Notes |
|---|---|---|
| Pending, Passed, Failed by origin x port | `Fundamental/Daily Miner/Database/Main/KC/kc_grading.parquet` | ICE daily certified-stock report, from 2023-07-18 |
| Daily certs by origin x port | `Fundamental/Daily Miner/Database/Main/KC/kc_certs.parquet` | LSEG KC-{origin}-{port}; the ICE report only has certs on some days |
| KC c1, c2, 1/2 spread, Rollex active spread | `Fundamental/Daily Miner/Database/Main/KC/price_link_kc.parquet` | c/lb, kept from 2015 |
| Origin exports to Belgium / US, Belgian / US imports by origin | `Fundamental/TDM Pro/Comprehensive TDM/Database/Coffee/` | HS 0901.11 green, tonnes x 16.67 = bags |
| Brazil Arabica / Robusta exports to Belgium, USA and total | `Fundamental/Cecafe Daily/Database/cecafe_destinations.csv` | K bags, from 2007 |

We read local copies rather than calling LSEG: the Daily Miner already pulls the same data, and the build needs no Workspace session.

## Method

- **Fresh pending** = change in Pending + Passed + Failed, per origin and port, per report day. Summed to months from Aug-2023.
- **Lead-lag**: correlation of monthly fresh pending with flow N months earlier, complete months only.
- **Auto fit** per origin: the source and lead (0-3 months, at least 18 months of overlap) with the best r. A lead of 1 month or more wins if its r is within 0.05 of the best, because only a lead gives a forecast.
- **Conversion** = sum of fresh pending / sum of lagged flow: the share of what ships to Belgium that is presented for grading.
- **Nowcast** = conversion x lagged flow, for fits with r >= 0.30.
- **Spreads**: spread = a + b ln(stock), with certs alone and with certs + pending. Fresh pending vs the roll-adjusted spread change 0-3 months later. Pipeline-implied spread adds the nowcast to today's pool.

## Caveats

| Topic | Note |
|---|---|
| Fresh pending | Change in pending + passed + failed, per report day (same as Daily Miner `kc_fresh_frame`). |
| Missing days | A missing ICE daily file loses that day's passed + failed, so the month is understated. |
| Certs | Daily from LSEG `kc_certs.parquet`; the ICE report only carries certs on some days. Kenya / Virginia have no LSEG RIC and keep the report value. |
| HS 0901.11 | TDM mixes Arabica and Robusta (Uganda, India, Tanzania, Brazil TDM). Use Cecafe for Brazil. |
| Imports | Booked at customs; EU transit coffee (via Rotterdam / Hamburg) can land in another country's imports. |
| US | Consumer market: only a few % of flow gets graded, so fits are weaker. |
| Nicaragua | TDM exports stop Dec-2023; only Belgian / US imports usable. |
| Sample | About 38 complete months since Aug-2023, both series seasonal. Auto-fit leads capped at 0-3 months. |

## Dashboard sections

Overview (KPIs, monthly fresh pending by origin, origin scorecard) · Origin Study (overlay, lead-lag, scatter, grading outcome, seasonality) · Brazil (Cecafe excess vs 5y normal, Belgium share, crop-year pace) · Nowcast · Spreads · Data (freshness, coverage, caveats).

## Run

```
python Code/build_db.py
streamlit run Dashboard/app.py
```

Task Scheduler: Program `cmd.exe`, Arguments `/c "<repo path>\Automator\run_update.bat"`, Mon-Fri after the Daily Miner run (for example 10:30).

Streamlit Cloud: repo `virataryaa/coffee-fresh-pending-vs-flow`, branch `main`, main file `Dashboard/app.py`.
