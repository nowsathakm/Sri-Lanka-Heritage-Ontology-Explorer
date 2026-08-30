# Sri Lanka Heritage Ontology Explorer — Streamlit App

A front-end for the Sri Lanka Heritage Ontology Explorer. Executes real
SPARQL 1.1 queries (via `rdflib`) against the Sri Lanka Heritage & Tourism ontology,
including facts materialised by the HermiT reasoner. A plain-English question box
translates to SPARQL via the Anthropic API — the API key lives only on the server
and is never sent to, or visible in, the browser.

## Files
- `app.py` — the Streamlit application
- `requirements.txt` — Python dependencies
- `ontology_materialized.ttl` — the ontology, with asserted **and** reasoner-inferred
  triples already materialised (see "Architecture note" below)

## Option A — Run locally

```bash
pip install -r requirements.txt
```

Provide your Anthropic API key one of two ways:

```bash
# Option 1: environment variable
export ANTHROPIC_API_KEY=sk-ant-...

# Option 2: local secrets file (create this yourself, do not commit it)
mkdir -p .streamlit
echo 'ANTHROPIC_API_KEY = "sk-ant-..."' > .streamlit/secrets.toml
```

Then run:

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically http://localhost:8501). The 8 preset
queries and the schema browser work even without an API key — only the free-text
question box needs it.

## Option B — Deploy for free on Streamlit Community Cloud

1. Create a **public or private GitHub repository** containing exactly these three
   files: `app.py`, `requirements.txt`, `ontology_materialized.ttl`.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **"New app"**, pick the repository/branch, and set the main file path to
   `app.py`.
4. Before or after deploying, open the app's **Settings → Secrets** and add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   This is stored encrypted by Streamlit and is never exposed to site visitors —
   it is only readable by the running server process via `st.secrets`.
5. Click **Deploy**. Your app will be live at `https://<your-app>.streamlit.app`,
   viewable by anyone with the link — no installation needed.

## Architecture

- The ontology was authored and validated in Protégé/OWL, then run through the
  **HermiT** reasoner offline. `ontology_materialized.ttl` bundles both the
  originally asserted triples and the additional triples HermiT derived (e.g.
  `rdf:type :UNESCOWorldHeritageSite`, and `:locatedInCountry` via the
  `locatedIn ∘ partOfRegion` property chain) — the same "materialise once, query
  many times" pattern used by production triple stores.
- The app queries this graph with `rdflib`'s full SPARQL 1.1 engine — a real,
  standards-compliant implementation, not a hand-rolled subset.
- The free-text question box sends the question to the Anthropic API **from this
  server**, asking Claude to translate it into SPARQL against the ontology's
  documented schema; the generated SPARQL is displayed to the user before being
  executed, so the translation step is fully auditable.
- Results whose correctness depends on the reasoner (Q7, Q8, and any free-text
  question resolving to those inferred properties) are visibly marked
  **INFERRED**; everything else is marked **ASSERTED**.
