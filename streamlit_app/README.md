# Sri Lanka Heritage Ontology Explorer — Streamlit App

A front-end for the Sri Lanka Heritage Ontology Explorer. Executes real
SPARQL 1.1 queries (via `rdflib`) against the Sri Lanka Heritage & Tourism ontology,
including facts materialised by the HermiT reasoner. A plain-English question box
translates to SPARQL via Claude — authenticated with **either** a direct Anthropic
API key **or** AWS Bedrock credentials, whichever you configure. Credentials live
only on the server and are never sent to, or visible in, the browser.

## Files
- `app.py` — the Streamlit application
- `requirements.txt` — Python dependencies
- `ontology_materialized.ttl` — the ontology, with asserted **and** reasoner-inferred
  triples already materialised (see "Architecture" below)

## Option A — Run locally

```bash
pip install -r requirements.txt
```

Provide credentials — **either** a direct Anthropic API key **or** AWS Bedrock
credentials (the app checks for a direct key first, and falls back to Bedrock
if that isn't set):

```bash
# Direct Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# OR: AWS Bedrock credentials instead
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1                                   # region where Claude is enabled in Bedrock
export BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-v1:0   # check the exact ID in your Bedrock console
```

Or, instead of environment variables, create a local secrets file (create this
yourself, do not commit it):

```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
ANTHROPIC_API_KEY = "sk-ant-..."
EOF
```

Then run:

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically http://localhost:8501). The 8 preset
queries and the schema browser work even with no credentials configured —
only the free-text question box needs them.

## Option B — Deploy for free on Streamlit Community Cloud

1. Create a **public or private GitHub repository** containing exactly these three
   files: `app.py`, `requirements.txt`, `ontology_materialized.ttl`.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **"New app"**, pick the repository/branch, and set the main file path to
   `app.py`.
4. Before or after deploying, open the app's **Settings → Secrets** and add
   **either**:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   **or**:
   ```toml
   AWS_ACCESS_KEY_ID = "..."
   AWS_SECRET_ACCESS_KEY = "..."
   AWS_REGION = "us-east-1"
   BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6-v1:0"
   ```
   This is stored encrypted by Streamlit and is never exposed to site visitors —
   it is only readable by the running server process via `st.secrets`.
5. Click **Deploy**. Your app will be live at `https://<your-app>.streamlit.app`,
   viewable by anyone with the link — no installation needed.

### Using AWS Bedrock instead of a direct API key

If you'd rather authenticate via AWS Bedrock (e.g. to use AWS free-trial credits
instead of paying Anthropic directly):

1. In the [Bedrock console](https://console.aws.amazon.com/bedrock/), go to
   **Model access** and enable access to the Claude model(s) you want — this is
   usually near-instant approval.
2. Note the exact model ID shown there (Bedrock model IDs differ from direct
   Anthropic API model names, and sometimes include a region prefix like `us.`)
   and set it as `BEDROCK_MODEL_ID`.
3. Create an IAM user (or role) with `bedrock:InvokeModel` permission, and
   generate an access key pair for it.
4. Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` as shown
   above — the app will detect these and use `AnthropicBedrock` automatically
   if no `ANTHROPIC_API_KEY` is set.

## Architecture

- The ontology was authored and validated in Protégé/OWL, then run through the
  **HermiT** reasoner offline. `ontology_materialized.ttl` bundles both the
  originally asserted triples and the additional triples HermiT derived (e.g.
  `rdf:type :UNESCOWorldHeritageSite`, and `:locatedInCountry` via the
  `locatedIn ∘ partOfRegion` property chain) — the same "materialise once, query
  many times" pattern used by production triple stores.
- The app queries this graph with `rdflib`'s full SPARQL 1.1 engine — a real,
  standards-compliant implementation, not a hand-rolled subset.
- The free-text question box sends the question to Claude **from this server**
  (via either the direct Anthropic API or AWS Bedrock — see above), asking it to
  translate the question into SPARQL against the ontology's documented schema;
  the generated SPARQL is displayed to the user before being executed, so the
  translation step is fully auditable.
- Results whose correctness depends on the reasoner (Q7, Q8, and any free-text
  question resolving to those inferred properties) are visibly marked
  **INFERRED**; everything else is marked **ASSERTED**.
