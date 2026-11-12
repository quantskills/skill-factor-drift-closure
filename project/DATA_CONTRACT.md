# Current data and execution contract

`data/weekly_slim.csv` is the frozen upstream weekly table. `data/panel_for_platform.csv` supplies the frozen 54 exported factor columns. `data/upstream_summary.json` identifies those columns and the historical selection protocol. `data/provenance.json` records original paths, snapshot hashes and the platform ML version. The current engine does not redownload market data or reselect factors.

The source scripts copied under `data/provenance/` establish that `fwd_ret` is weekly `open(t+5)/open(t+1)-1`: four observations of holding, with the label available five observations after the signal. It is not five weeks of holding. Actual next-trading-day execution is not independently reconciled with these weekly open prices. Point-in-time membership and input-factor publication timing are inherited from upstream, not independently certified by the current package.

The common observable pool requires upstream membership, upstream entry eligibility, a finite frozen Ridge score and finite current factor columns. It never filters on future return availability. Each arm ranks that same pool and selects 50 stocks. Equal weight means the direct mean of the exported factor columns; those columns have already been transformed upstream.

Some individual future returns are missing even when the global label-maturity calendar is complete. Current baseline accounting imputes them as zero, records their counts, and repeats the experiment with -100% imputation as sensitivity. That sensitivity is not a formal worst-case bound for the hedged portfolio. Missing labels materially affect the absolute return estimate; report them.

Four phase accounts rebalance every four observations. Costs charge the union of old and new holdings, including sales and weight drift after past returns. Each phase starts from cash and initial equity 1. Long-minus-pool hedge weights are not an estimated beta hedge. Transaction costs are 8bp per side plus annualized 2% short borrow on the four-week leg. Impact, borrow availability and failed exits are not modeled. Reported terminal returns average four phase accounts; they are not a synchronous live NAV.

The first 120 mature health IC observations establish the upstream default health baseline, ending before the evaluation starts. Project IC calibration uses only 2024. Training ends one extra observation before the newest mature label, matching the conservative platform fold: 156 training dates, five excluded dates, one test date, a six-observation distance from final training date to test date.

Current statistical inference aligns paired action returns by phase/cycle. IID and circular block bootstrap retain the whole contrast vector per sampled cycle. The 18-member family is declared in `config/audit_v2.json`. Health parameter sweeps do not feed policy selection. The historical evaluation has already been inspected; a future confirmation requires new data.
