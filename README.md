# TSTT Board Report

A Streamlit dashboard that **is** the monthly board pack. Both exporters screenshot the live
app, so there is no separate report template — what the dashboard looks like is what the
board sees. Sixteen pages covering group financials, the three lines of business, Amplia and
DPDI, exported to PowerPoint or Word.

Trinidad & Tobago's incumbent telco. All figures TT$.

---

## Running it

```powershell
.\restart.ps1              # kills whatever holds port 8501, then relaunches
```

Or directly:

```powershell
& "$env:USERPROFILE\venvs\tstt_board\Scripts\python.exe" -m streamlit run app.py
```

The venv lives **outside** OneDrive at `~\venvs\tstt_board` deliberately — an in-repo `.venv`
syncs between machines and carries the other machine's compiled wheels, which breaks
pandas/numpy on import. Any `venv/` or `.venv/` inside the repo is stale; don't use it.

`pip install -r requirements.txt`, plus `playwright install chromium` once for the exporters.

---

## Data

One workbook is the single source of truth: **`TSTT_Master_Data_Template.xlsx`**.

`utils/data_loader.py` fetches it live from OneDrive via Microsoft Graph when credentials are
configured (`[graph]` in `.streamlit/secrets.toml`, or `GRAPH_TENANT_ID` / `GRAPH_CLIENT_ID` /
`GRAPH_CLIENT_SECRET` / `GRAPH_USER_UPN`). Without them it reads the local OneDrive-synced
copy, so local dev needs no secrets. Everything is cached with `@st.cache_data(ttl=86400)`.

Workbook conventions — get these wrong and numbers are silently off by 10⁶:

- **Raw TTD**, always. `1500000`, never `1.5`. The dashboard divides by 1,000,000 for display.
- **Percentages as real percentages.** `2.5`, not `0.025`.
- **Months as `Mon-YY`** (`Apr-26`). Parsed strictly, then loosely; years outside 2000–2099 are
  rejected as Excel serial-0 artefacts.
- **Every sheet has a 4-row header**: title / subtitle / column names / descriptions. Readers
  use `header=2, skiprows=[3]`. A sheet added without that shape will not parse.
- **Fiscal year is April–March.** Month ≥ 4 → FY starts that calendar year; month < 4 → prior
  year. Applies to every YTD aggregate, CAPEX budget and period comparison.

### Sheets → `load_all_data()` keys

| Sheet | Key(s) |
|---|---|
| `P&L_Segments` | `Financial_Monthly`, `PnL_Breakdown`, `KPI_Summary`, `EBITDA_Bridge`, `AMPLIA_Financial` |
| `OPEX_Detail` | `OPEX` |
| `Consumer_Products` | `Consumer_Sales` |
| `Business_Products` | `Business_Sales`, `Business_Sales_MRR` |
| `DPDI_Products` | `DPDI` |
| `Amplia_Commercial` | `AMPLIA_Commercial` |
| `Cash_CAPEX`, `Collections_Billing` | `Cash_CAPEX` |
| `Pipeline`, `Renewals` | `Pipeline`, `Renewals` |

`PP_Plans` and `WTTx_Plans` are always-empty placeholders — those sheets are not in the
master template. Check for empties before using them.

Separately cached loaders: `load_ar()`, `load_collections_billing()`, `load_prepaid_arpu()`,
`load_prepaid_data_usage()`, `load_postpaid_plans()`, `load_wttx_categories()`,
`load_porting_trend()`.

---

## Layout

```
app.py                  Executive Summary (the Home page)
pages/                  0-15, numeric prefix = sidebar order
utils/
  data_loader.py        Graph fetch + every sheet reader; all caching lives here
  month_selector.py     Focus-month control and filter_data_to_month()
  theme.py              Dark/light toggle (see below)
  charts.py             Palette, base Plotly layout, line/bar/stacked/waterfall builders,
                        inject_css(), page_header(), kpi_card()
  consumer_common.py    Sparklines and KPI-card HTML shared by the consumer pages
  rag.py                RAG thresholds, from the Key Risk Indicator doc
tools/
  pptx_screenshot_export.py   Owns browser capture, page discovery and slicing
  docx_screenshot_export.py   Imports all of the above; adds Word page assembly
assets/style.css        All app chrome; written in the dark palette
```

Pages: Financial Performance, Revenue Mix & Variance, Enterprise Scorecard, OPEX & Cost,
Cash & CAPEX, Consumer Sales, Prepaid, Postpaid, WTTx, Number Porting, Business Sales, DPDI,
Amplia Financial, Amplia Commercial, Export, Rev by LOB.

Every page starts with `inject_css()` then `focus_month_selector()`. Both are required —
the first installs the theme hook, the second renders the sidebar controls.

---

## Theming — read this before touching any colour

The dashboard has a **runtime dark/light toggle**: "Report style" in the sidebar, or `?theme=`
in the URL. Dark is the default and is the PowerPoint pack; light is the Word one.

**Pages are written in the dark palette. That is the source of truth.** Light is *derived* at
render time by `COLOUR_MAP` in `utils/theme.py`, which patches `DeltaGenerator.markdown` and
`.plotly_chart` once so that sixteen pages of hardcoded colour need no per-theme code. On dark
it is a no-op.

The direction is not arbitrary: the light design collapses ten different dark greys onto
`#5B6675` and 71 uses of `white` onto `#1F2328`, so light → dark cannot be recovered.

> **When you add a colour anywhere, add its dark → light pair to `COLOUR_MAP` in the same
> change.** An unmapped dark literal renders unchanged on the light theme, which on white
> usually means invisible.

To check the map after a colour change: tint every dark source and diff against the shipped
light files (commit `46b2394`) — they should match except for lines added since.

Standards: cards `#161B22`, app background `#0D1117`, borders `#2a2a4a`/`#21262d`, body text
`white`. Donut separators and dot outlines take the *card* colour, not ink. AOP/PY reference
lines need more alpha as dark ink on white (0.27/0.20 → 0.42/0.34) — already in the map.

Type sizes are set for the export, not the screen: pages read at a distance on a projected
slide, so titles and card values run far larger than `charts.py`'s own builders default to.
Match the sizes already on the page you are editing rather than any global default.

---

## Exporting

The Export page builds either format; the exporters also run standalone:

```powershell
python tools\pptx_screenshot_export.py --theme dark  --focus-month Jun-26
python tools\docx_screenshot_export.py --theme light --pages "Consumer Sales,DPDI"
```

Headless Chromium walks every page at `?embed=true` (which hides the sidebar), screenshots it
full-page, and slices anything taller than one slide/page. `--url` reuses a running server;
otherwise a dedicated one is launched on 8599. A full pack takes 2–3 minutes.

`--theme`, `--focus-month`, `--page`/`--pages`, `--out`, `--viewport-width`, `--no-split`,
`--headed`. The slide/page fill follows the theme via `BACKGROUND_RGB`.

---

## Conventions that are easy to get wrong

- **Focus month** drives everything. It lives in session state, is seeded from `?focus_month=`
  (how the exporter pins a month), and pages call `filter_data_to_month()`. It defaults to the
  last month in `Financial_Monthly`, which runs to `Mar-27` on budget rows — so pages whose
  data ends earlier must clamp to their own last populated month rather than assume the focus
  month exists (see DPDI and Rev by LOB).
- **Cost metrics invert the variance sign.** Direct Costs, OPEX: variance is `AOP − Actual`, so
  underspend is positive and green. Revenue metrics are `Actual − AOP`.
- **All "vs PY" card lines** use `rev_var_rag`'s three tiers: green ≥ 0, amber ≥ −10%, red < −10%.
- **Subscriber movement** is derived differently per page: Prepaid back-calculates churn from
  opening/closing/gross adds, while Postpaid and WTTx use the `Churn_Pct` column directly.
- **Rev by LOB PY** is the 12-month lag of `<segment>_Rev`, *not* the `<segment>_Rev_PY`
  columns — those are only populated Apr-25…Apr-26 and understate PY roughly fourfold.
- **Commit `6cdad52` is not a pure recolour.** It also carries the Business Sales AOP wiring,
  the Direct Costs cost convention and the Financial Performance EBITDA override. Never revert
  it wholesale to change themes.

---

## Not part of the working app

- `build_board_data.py`, `load_fy2027_opex.py` — ETL against `TSTT_Board_Data.xlsx`, the data
  source superseded by the master template. Legacy.
- `create_master_template.py` — generates the master workbook's structure; useful as a schema
  reference, not run routinely.
- `utils/ar_loader.py` — unused; `load_ar()` in `data_loader.py` is the live one.
- `DATA_UPDATE_GUIDE.txt` — longer written guide, last revised May 2026, so it predates the
  export pages, Rev by LOB and the theme toggle.
- Workbooks and extracts (`*.xlsx`, `*.tsv`, `*.docx`) and `exports/` are gitignored — data is
  pulled from OneDrive, never committed.
