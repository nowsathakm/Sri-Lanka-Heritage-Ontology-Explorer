"""
Sri Lanka Heritage & Tourism Ontology Explorer — Streamlit edition.

Runs a real SPARQL 1.1 engine (rdflib) against the ontology (asserted +
HermiT-materialised inferred triples). Authenticates the NL-search feature
via EITHER a direct Anthropic API key OR AWS Bedrock credentials — whichever
is configured. Credentials live only in Streamlit secrets / environment
variables on the server; they are never sent to, or visible in, the browser.

Run locally (direct Anthropic API key):
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...      (or use .streamlit/secrets.toml)
    streamlit run app.py

Run locally (AWS Bedrock instead):
    pip install -r requirements.txt
    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_REGION=us-east-1                        (region where Claude is enabled in Bedrock)
    export BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-v1:0   (check exact ID in your Bedrock console)
    streamlit run app.py

Deploy for free on Streamlit Community Cloud:
    1. Push this folder to a GitHub repo (app.py, requirements.txt, ontology_materialized.ttl).
    2. Go to https://share.streamlit.io , sign in, "New app", pick the repo/branch, main file = app.py.
    3. In the app's Settings -> Secrets, add EITHER:
           ANTHROPIC_API_KEY = "sk-ant-..."
       OR:
           AWS_ACCESS_KEY_ID = "..."
           AWS_SECRET_ACCESS_KEY = "..."
           AWS_REGION = "us-east-1"
           BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6-v1:0"
    4. Deploy. Credentials are stored encrypted server-side and are never exposed to visitors.
"""

import os
import re
import streamlit as st
from rdflib import Graph
from anthropic import Anthropic, AnthropicBedrock

st.set_page_config(page_title="Sri Lanka Heritage Ontology Explorer", page_icon="🛕", layout="wide")

ONTOLOGY_PATH = os.path.join(os.path.dirname(__file__), "ontology_materialized.ttl")
DEFAULT_DIRECT_MODEL = "claude-sonnet-4-6"
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-6-v1:0"

PREFIXES = """
PREFIX : <http://www.srilanka-heritage.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

PRESETS = [
    {
        "id": "Q1", "label": "Sites by province", "type": "asserted",
        "cq": "Which tourist sites are located in each province of Sri Lanka?",
        "sparql": PREFIXES + """
SELECT ?siteLabel ?provinceLabel WHERE {
    ?site :locatedIn ?province .
    ?site rdfs:label ?siteLabel .
    ?province rdfs:label ?provinceLabel .
} ORDER BY ?siteLabel"""
    },
    {
        "id": "Q2", "label": "Activity types", "type": "asserted",
        "cq": "What types of activities are available across Sri Lankan tourist sites?",
        "sparql": PREFIXES + """
SELECT ?activityLabel WHERE {
    ?activity rdfs:subClassOf :Activity .
    ?activity rdfs:label ?activityLabel .
    FILTER(?activity != :AdventureActivity)
} ORDER BY ?activityLabel"""
    },
    {
        "id": "Q3", "label": "Sites under $10", "type": "asserted",
        "cq": "Which tourist sites cost less than $10 to enter?",
        "sparql": PREFIXES + """
SELECT ?siteLabel ?fee WHERE {
    ?site :hasEntryFeeUSD ?fee .
    ?site rdfs:label ?siteLabel .
    FILTER(?fee < 10.0)
} ORDER BY ?fee"""
    },
    {
        "id": "Q4", "label": "Elevation (optional)", "type": "asserted",
        "cq": "What is the elevation of each tourist site, where recorded?",
        "sparql": PREFIXES + """
SELECT DISTINCT ?siteLabel ?elevation WHERE {
    ?site rdf:type/rdfs:subClassOf* :TouristSite .
    ?site rdfs:label ?siteLabel .
    OPTIONAL { ?site :hasElevationMeters ?elevation }
} ORDER BY ?siteLabel"""
    },
    {
        "id": "Q5", "label": "Highest entry fee", "type": "asserted",
        "cq": "What is the highest entry fee charged at any tourist site?",
        "sparql": PREFIXES + """
SELECT (MAX(?fee) AS ?maxFee) WHERE {
    ?site :hasEntryFeeUSD ?fee .
}"""
    },
    {
        "id": "Q6", "label": "Sites per province (ranked)", "type": "asserted",
        "cq": "How many tourist sites are there in each province, ranked from most to least?",
        "sparql": PREFIXES + """
SELECT ?provinceLabel (COUNT(?site) AS ?siteCount) WHERE {
    ?site :locatedIn ?province .
    ?province rdfs:label ?provinceLabel .
} GROUP BY ?provinceLabel ORDER BY DESC(?siteCount)"""
    },
    {
        "id": "Q7", "label": "UNESCO sites (inferred)", "type": "inferred",
        "cq": "Which tourist sites are UNESCO World Heritage Sites?",
        "sparql": PREFIXES + """
SELECT ?siteLabel WHERE {
    ?site rdf:type :UNESCOWorldHeritageSite .
    ?site rdfs:label ?siteLabel .
} ORDER BY ?siteLabel"""
    },
    {
        "id": "Q8", "label": "Country (property chain, inferred)", "type": "inferred",
        "cq": "Which country is each tourist site located in?",
        "sparql": PREFIXES + """
SELECT ?siteLabel ?countryLabel WHERE {
    ?site :locatedInCountry ?country .
    ?site rdfs:label ?siteLabel .
    ?country rdfs:label ?countryLabel .
} ORDER BY ?siteLabel"""
    },
]

SCHEMA_NOTE = """
Ontology namespace prefix ":" = http://www.srilanka-heritage.org/ontology#
Classes include: TouristSite, HeritageSite, NaturalSite, CulturalSite, ReligiousSite, ArchaeologicalSite,
BuddhistTemple, HinduKovil, ChristianChurch, MosqueSite, AncientCity, FortSite, CaveTempleSite,
NationalPark, Beach, Waterfall, MountainPeak, WildlifeSanctuary, Museum, TeaPlantation, BotanicalGarden,
Province, Country, Activity, and the defined classes UNESCOWorldHeritageSite, FreeEntrySite, AdventureSite,
ReligiousPilgrimageSite.
Object properties: locatedIn (TouristSite->Province, functional), hasActivity (TouristSite->Activity),
partOfRegion (transitive), nearbyTo (symmetric), locatedInCountry (TouristSite->Country, derived via
property chain locatedIn o partOfRegion).
Data properties: hasEntryFeeUSD (decimal), isUNESCOListed (boolean), yearInscribed (int),
hasElevationMeters (decimal), siteDescription (string).
Every class/property/individual has an rdfs:label.
Activity individuals (use with hasActivity): :HikingActivity, :SafariActivity, :SurfingActivity,
:PilgrimageActivity, :SightseeingActivity, :PhotographyActivity.
"""

SYSTEM_PROMPT = f"""You translate a plain-English question about a Sri Lankan tourism/heritage OWL \
ontology into a single SPARQL 1.1 query. Return ONLY the SPARQL query text — no markdown fences, no \
explanation, no comments before or after.

{SCHEMA_NOTE}

Every site in this ontology is already located in Sri Lanka — do not add a country filter (e.g. via \
locatedInCountry) unless the question specifically asks about country/nationality; it only adds a chance \
to get the join wrong for no benefit.

hasActivity must point to the ACTIVITY INDIVIDUAL (e.g. :HikingActivity, :SurfingActivity), never the bare \
class name (:Hiking, :Surfing) — a triple like "?site :hasActivity :Hiking" will never match anything, \
because Hiking is a class, not an individual. Example — correct pattern for "which sites offer hiking?":
SELECT ?siteLabel WHERE {{
    ?site :hasActivity :HikingActivity .
    ?site rdfs:label ?siteLabel .
}}

Always bind rdfs:label into a variable for any entity you want to display by name, since raw URIs are \
not human-friendly. The graph you will query already includes reasoner-materialised inferred triples \
(e.g. rdf:type :UNESCOWorldHeritageSite, and :locatedInCountry), so you may query those directly as if \
they were asserted. Because a single site individual is asserted with multiple rdf:type values (its \
specific class plus any inferred defined classes), always use SELECT DISTINCT when your query walks a \
rdf:type/rdfs:subClassOf* path or otherwise groups by class membership, to avoid duplicate rows."""


@st.cache_resource(show_spinner="Loading ontology…")
def load_graph():
    g = Graph()
    g.parse(ONTOLOGY_PATH, format="turtle")
    return g


def run_sparql(query_text):
    g = load_graph()
    qres = g.query(query_text)
    cols = [str(v) for v in qres.vars]
    rows = []
    for row in qres:
        rows.append([str(cell) if cell is not None else None for cell in row])
    return cols, rows


def _secret_or_env(key, default=None):
    try:
        val = st.secrets.get(key, None)
    except Exception:
        val = None
    return val or os.environ.get(key, default)


def get_client():
    """Returns (provider, client, model_id) using whichever credentials are configured.
    Prefers a direct Anthropic API key; falls back to AWS Bedrock credentials."""
    api_key = _secret_or_env("ANTHROPIC_API_KEY")
    if api_key:
        model_id = _secret_or_env("ANTHROPIC_MODEL", DEFAULT_DIRECT_MODEL)
        return "direct", Anthropic(api_key=api_key), model_id

    aws_access_key = _secret_or_env("AWS_ACCESS_KEY_ID")
    aws_secret_key = _secret_or_env("AWS_SECRET_ACCESS_KEY")
    if aws_access_key and aws_secret_key:
        aws_region = _secret_or_env("AWS_REGION", "us-east-1")
        model_id = _secret_or_env("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL)
        client = AnthropicBedrock(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
        )
        return "bedrock", client, model_id

    return None, None, None


def nl_to_sparql(question):
    provider, client, model_id = get_client()
    if client is None:
        raise RuntimeError(
            "No credentials configured on the server. Set either ANTHROPIC_API_KEY, "
            "or AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (for AWS Bedrock), via "
            ".streamlit/secrets.toml locally or Settings -> Secrets on Streamlit Cloud."
        )
    resp = client.messages.create(
        model=model_id,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    text = re.sub(r"^```(sparql)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    text = re.sub(r"(?im)^\s*PREFIX\s+\S*:\s*<[^>]*>\s*$", "", text).strip()
    text = PREFIXES.strip() + "\n" + text
    return text


# ---------------- UI ----------------

st.markdown(
    """
    <style>
    .stButton>button {
        border: 1px solid #B8860B;
        border-radius: 8px;
        color: #16232A;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stButton>button:hover {
        background-color: #B8860B;
        color: #F6F0E4;
        border-color: #B8860B;
    }
    [data-testid="stExpander"] summary {
        background-color: #EDE4D0;
        border-radius: 8px;
        font-weight: 600;
        color: #16232A;
    }
    div[data-testid="stCodeBlock"] pre {
        border: 1px solid #B8860B55;
    }
    </style>
    <div style="text-align:center; padding: 1.2rem 1rem; margin-bottom: 1rem;
                background: linear-gradient(135deg, #16232A 0%, #20323C 100%);
                border-radius: 12px; border: 1px solid #B8860B;">
        <h1 style="margin:0.1rem 0; color:#F6F0E4;">🛕 Sri Lanka Heritage &amp; Tourism Ontology Explorer</h1>
        <p style="color:#D9A93B; max-width:700px; margin:0.5rem auto 0 auto; font-size:0.95rem;">
            Ask a question in plain English, or pick one of the eight tested competency questions.
            Every answer is retrieved by executing a real SPARQL query (via rdflib) against the ontology.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "active_sparql" not in st.session_state:
    st.session_state.active_sparql = PRESETS[0]["sparql"]
    st.session_state.active_meta = PRESETS[0]
    st.session_state.cols = None
    st.session_state.rows = None
    st.session_state.error = None


def execute_and_store(sparql, meta):
    try:
        cols, rows = run_sparql(sparql)
        st.session_state.cols = cols
        st.session_state.rows = rows
        st.session_state.active_sparql = sparql
        st.session_state.active_meta = meta
        st.session_state.error = None
    except Exception as e:
        st.session_state.error = str(e)
        st.session_state.cols = None
        st.session_state.rows = None


with st.form(key="ask_form", clear_on_submit=False):
    col_q, col_btn = st.columns([5, 1])
    with col_q:
        question = st.text_input("Ask a question", placeholder="e.g. Which free sites offer hiking in Uva Province?", label_visibility="collapsed")
    with col_btn:
        ask_clicked = st.form_submit_button("Ask", use_container_width=True)

if ask_clicked and question.strip():
    with st.spinner("Translating to SPARQL…"):
        try:
            sparql = nl_to_sparql(question)
            execute_and_store(sparql, {"id": "NL", "label": "Your question", "type": None, "cq": question})
        except Exception as e:
            st.session_state.error = str(e)

st.caption("Or try a tested competency question:")
preset_cols = st.columns(4)
for i, p in enumerate(PRESETS):
    with preset_cols[i % 4]:
        if st.button(f"{p['id']} · {p['label']}", key=p["id"], use_container_width=True, help=p["cq"]):
            execute_and_store(p["sparql"], p)

st.divider()

if st.session_state.error:
    st.error(st.session_state.error)

meta = st.session_state.active_meta
if meta.get("cq"):
    badge_col, _ = st.columns([3, 1])
    with badge_col:
        st.markdown(f"**{meta['cq']}**")
    if meta.get("type") == "inferred":
        st.markdown(":violet-background[**INFERRED** — this fact was derived by the reasoner, not asserted directly]")
    elif meta.get("type") == "asserted":
        st.markdown(":green-background[**ASSERTED** — directly stated in the ontology]")

st.caption("Generated SPARQL")
st.code(st.session_state.active_sparql.strip(), language="sparql")

if st.session_state.cols is not None:
    st.caption(f"Result ({len(st.session_state.rows)} row{'s' if len(st.session_state.rows) != 1 else ''})")
    if st.session_state.rows:
        st.dataframe(
            {col: [row[i] for row in st.session_state.rows] for i, col in enumerate(st.session_state.cols)},
            use_container_width=True,
        )
    else:
        st.info("No results.")

with st.expander("View ontology classes & properties"):
    st.markdown(SCHEMA_NOTE)

with st.expander("How this app works / architecture"):
    st.markdown(
        """
1. The ontology (`ontology_materialized.ttl`) includes both asserted facts **and** the facts materialised by
   running the HermiT reasoner offline (e.g. UNESCO classifications and the `locatedInCountry` property-chain
   results) — the same pattern real triple stores use.
2. Typing a question calls the Anthropic API **from this server** (never from the browser), using an API key
   stored in Streamlit secrets — it is never sent to or visible in the client.
3. The returned SPARQL text (shown above) is executed by **rdflib**, a full SPARQL 1.1 engine, against the
   loaded graph.
4. Preset queries Q7 and Q8 are stamped **INFERRED** because their answers depend on knowledge the reasoner
   derived — UNESCO classification via an equivalent-class definition, and a site's country via a property-chain
   axiom — neither of which is asserted anywhere in the ontology.
        """
    )

st.caption("Sri Lanka Heritage & Tourism Sites Ontology · Semantic Web and Ontologies coursework")
