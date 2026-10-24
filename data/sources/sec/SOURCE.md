# Public Nasdaq symbol directory snapshots

These files were downloaded from the public Nasdaq Trader symbol directory on
2026-10-24. Despite this folder's initial `sec` name, they are **Nasdaq data**, not
an SEC bulk export. The attempted direct SEC download returned HTTP 403 and is
not used in this catalog.

- `nasdaqlisted.txt`: https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt
- `otherlisted.txt`: https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt
- Definitions: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs
- Both source creation timestamps: `1023202621:31`; timezone not specified.

Original Nasdaq rights and terms apply. The repository's code license does not
relicense external source data; no open-data license is asserted. Source bytes
are preserved unchanged and checked by SHA-256 in `data/catalogs/nasdaq.json`.
`nasdaq_exclusions.json` is the generated row-level exclusion audit.

See `docs/CATALOG_COMPANIES.md` for scope, limitations and reproducible import.
