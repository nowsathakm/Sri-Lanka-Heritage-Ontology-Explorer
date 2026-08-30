# Sri Lanka Heritage Ontology Explorer

![OWL](https://img.shields.io/badge/OWL-2-blue) ![SPARQL](https://img.shields.io/badge/SPARQL-1.1-orange) ![Protégé](https://img.shields.io/badge/Built%20with-Protégé-6aa84f) ![Reasoner](https://img.shields.io/badge/Reasoner-HermiT-purple) ![Streamlit](https://img.shields.io/badge/App-Streamlit-ff4b4b)

An OWL ontology modelling Sri Lanka's tourism and cultural heritage domain — heritage, natural, and cultural sites, their provinces, activities, and attributes like entry fee and UNESCO status. Built in Protégé and validated with the HermiT reasoner, it uses disjoint/equivalent classes, functional/transitive/symmetric properties, a property chain, and cardinality restrictions to support real logical inference. Includes 8 tested SPARQL queries and a Streamlit app for querying the ontology in plain English.

Coursework project for **Semantic Web and Ontologies** — Local-Domain Ontology Design, Reasoning and SPARQL.

---

## Contents

- [Overview](#overview)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Ontology Summary](#ontology-summary)
- [Getting Started](#getting-started)
  - [Open the ontology in Protégé](#1-open-the-ontology-in-protégé)
  - [Run the Streamlit app](#2-run-the-streamlit-app)
- [SPARQL Queries](#sparql-queries)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Overview

This project designs and implements an OWL ontology for **Sri Lankan tourism and cultural heritage** — one of the suggested local domains for the coursework. It models tourist sites (heritage, natural, and cultural), the provinces they're located in, the activities they offer, and attributes such as entry fee, UNESCO status, and elevation.

Beyond basic class modelling, the ontology is built to support genuine reasoner-driven inference: UNESCO World Heritage status, adventure-site classification, and even a site's *country* are never asserted directly — they're derived entirely by the HermiT reasoner from simpler asserted facts, via equivalent-class definitions and a property chain.

## Features

- 🏛️ **25+ classes** across three taxonomies (site type, province, activity), with a fully disjoint sibling hierarchy
- 🔗 **7 object properties** and **5 data properties**, including functional, transitive, symmetric, and property-chain relations
- 🧠 **4 defined (equivalent) classes** whose membership is left entirely to the reasoner — not hand-assigned
- 🗺️ **21 real, richly-attributed individuals** (Sigiriya, Temple of the Tooth, Yala National Park, Adam's Peak, and more)
- 🔍 **8 tested SPARQL queries** covering basic SELECT, FILTER, OPTIONAL, aggregation, GROUP BY/ORDER BY, and reasoning-dependent retrieval
- 💬 **Natural-language querying** via a Streamlit app — ask a question in plain English, see the generated SPARQL, and get results from a real SPARQL 1.1 engine (`rdflib`)

## Repository Structure

```
sri-lanka-heritage-ontology-explorer/
├── README.md                          # you are here
├── ontology/
│   ├── SriLankaHeritage.owl           # RDF/XML — open directly in Protégé
│   ├── SriLankaHeritage.ttl           # Turtle — same content, human-readable
│   └── ontology_diagram.png           # class hierarchy & key properties diagram
└── streamlit_app/
    ├── app.py                         # Streamlit front-end (NL search + presets)
    ├── requirements.txt
    ├── ontology_materialized.ttl      # ontology + HermiT-inferred triples baked in
    └── README.md                      # app-specific setup & deployment instructions
```

## Ontology Summary

| | |
|---|---|
| **Namespace** | `http://www.srilanka-heritage.org/ontology#` |
| **Classes** | `TouristSite` → `HeritageSite` \| `NaturalSite` \| `CulturalSite` (+ leaf types), `Province` (9), `Activity` (6) |
| **Object properties** | `locatedIn` (functional), `hasActivity`, `partOfRegion` (transitive), `nearbyTo` (symmetric), `locatedInCountry` (property chain) |
| **Data properties** | `hasEntryFeeUSD`, `isUNESCOListed`, `yearInscribed`, `hasElevationMeters`, `siteDescription` |
| **Defined classes** | `UNESCOWorldHeritageSite`, `FreeEntrySite`, `AdventureSite`, `ReligiousPilgrimageSite` |
| **Reasoner** | HermiT — consistency and all inferences verified programmatically |


## Getting Started

### 1. Open the ontology in Protégé

1. Install [Protégé](https://protege.stanford.edu/) (free).
2. Open `ontology/SriLankaHeritage.owl`.
3. Run **Reasoner → HermiT → Start reasoner** to see inferred classifications.
4. Use the **SPARQL Query** tab to run any of the queries listed below.

### 2. Run the Streamlit app

```bash
cd streamlit_app
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # needed only for the natural-language search box
streamlit run app.py
```

See `streamlit_app/README.md` for free cloud deployment instructions (Streamlit Community Cloud) so the app can be shared as a link with no installation required on the viewer's end.

## SPARQL Queries

| # | Type | Competency question |
|---|---|---|
| Q1 | Basic SELECT | Which tourist sites are located in each province? |
| Q2 | Basic SELECT | What types of activities are available? |
| Q3 | FILTER | Which sites cost less than $10 to enter? |
| Q4 | OPTIONAL | What is each site's elevation, where recorded? |
| Q5 | Aggregation (MAX) | What is the highest entry fee charged? |
| Q6 | GROUP BY / ORDER BY | How many sites per province, ranked? |
| Q7 | Reasoning | Which sites are UNESCO World Heritage Sites? *(inferred)* |
| Q8 | Reasoning | Which country is each site located in? *(inferred via property chain)* |

Full query text, results, and interpretation for each are in `docs/Assignment_Report.docx`, Section 5.

## Architecture

```
 ┌────────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
 │  Protégé + HermiT   │ ───▶ │  Materialised     │ ───▶ │  rdflib (SPARQL 1.1)│
 │  (offline reasoning)│      │  ontology (.ttl)  │      │  query engine        │
 └────────────────────┘      └──────────────────┘      └──────────┬──────────┘
                                                                    │
                              ┌──────────────────┐                 ▼
                              │  Anthropic API     │◀── question ──┤  Streamlit app
                              │  (server-side only)│──── SPARQL ──▶│  (app.py)
                              └──────────────────┘                 │
                                                                    ▼
                                                            results + asserted/
                                                            inferred labelling
```

Reasoning happens **offline** in Protégé/HermiT; the inferred triples are materialised into the shipped `.ttl` file so the deployed app can use a real, lightweight, standards-compliant SPARQL engine without bundling a Java reasoner.

## Tech Stack

- **Ontology:** OWL 2, Protégé, HermiT reasoner
- **Query layer:** `rdflib` (Python, full SPARQL 1.1)
- **NL → SPARQL:** Anthropic API (Claude)
- **App:** Streamlit
- **Diagram:** Graphviz

## License

This project is licensed under the [MIT License](LICENSE) — you're free to use, modify, and distribute this code, provided the original copyright notice is retained.
