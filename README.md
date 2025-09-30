# Finance AI Assistant (MVP)

A privacy-first personal finance assistant. Upload transactions (CSV/OFX/QFX), normalize and categorize them (rules + AI-ready hooks), compute insights, and view a clean dashboard in Streamlit.

## Features (MVP)
- Upload CSV or OFX/QFX files.
- Normalize, deduplicate, and enrich transactions (merchant, MCC guess).
- Hybrid categorization: rules with hooks for models/LLM (edge cases).
- Insights: monthly summary, top categories/merchants, anomaly flags.
- Commentary: human-readable insights with citations to metrics (no external LLM required for MVP).
- Storage: local SQLite (`data/finance.db`).

## Project Structure
```
.
├── app.py                      # Streamlit entrypoint
├── requirements.txt
├── sample_data/
│   └── transactions_sample.csv
├── finance_ai/
│   ├── __init__.py
│   ├── config.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parser_csv.py
│   │   └── parser_ofx.py
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── normalize.py
│   │   ├── dedupe.py
│   │   └── enrich.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   └── repository.py
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── categorizer.py
│   │   ├── insights.py
│   │   └── commentary.py
│   └── ui/
│       ├── __init__.py
│       └── components.py
└── .streamlit/
    └── config.toml
```

## Quickstart
1. Create a virtual environment (recommended) and install deps:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Run the app:
```
streamlit run app.py
```
3. Upload `sample_data/transactions_sample.csv` to try it out.

## Notes
- PDFs are a future stretch (bank-specific templates). The ingestion layer is structured to add parsers.
- For privacy, all data stays local in SQLite. You can delete `data/` to remove state.
- LLM usage can be added via environment variables and a provider of your choice; current MVP does not call external APIs.

## License
MIT
