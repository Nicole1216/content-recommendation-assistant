# Sales Enablement Assistant

An agentic AI system for Udacity Enterprise sellers that provides intelligent, evidence-based responses to customer questions, tailored to specific stakeholder personas (CTO, HR, L&D).

## Overview

The Sales Enablement Assistant helps sellers quickly answer questions like:
- "Do we have GenAI content for non-technical roles?"
- "Customer wants to upskill 200 Data Analysts in 6 months—what should I propose?"
- "Do you cover Python hands-on with real projects?"

It retrieves information from two sources (catalog and CSV details), validates claims, and generates persona-specific responses with intelligent skill matching and semantic understanding.

## Architecture

The system implements a multi-agent architecture with intelligent semantic understanding:

### Core Agents
1. **Router Agent**: Classifies questions into task types (discovery, recommendation, skill validation) and extracts customer context
2. **Specialist Agents**:
   - CatalogSearch: Searches and ranks programs from catalog
   - CSVDetails: Retrieves detailed curriculum information from real CSV data
   - Comparator: Compares programs across 6 evaluation dimensions
3. **Composer Agent**: Writes final seller-facing responses tailored to persona
4. **Critic Agent**: Validates responses for evidence support, completeness, and persona fit

### Semantic Layer (Phase 3)
The system includes a **Skill Semantic Resolver** that enhances search with:
- **Alias Mapping**: Maps synonyms to canonical skills (e.g., "LLM" → "generative_ai")
- **Taxonomy Disambiguation**: Detects skill intents via context (e.g., "Python for analysts" vs "Python for ML engineers")
- **Fuzzy Matching**: Recovers from typos and variations (e.g., "Pyton" → "Python")
- **Optional Embeddings**: Semantic similarity matching (feature flag)

This allows sellers to use natural language without worrying about exact terminology.

### Unified Catalog API Integration (Phase 3.5)
The system integrates with the **Udacity Unified Catalog API** as the discovery layer:
- **Catalog API**: Answers "Do we have X?" - Fast discovery and high-level coverage
- **CSV Data**: Answers depth, skills, tools, prerequisites - Deep verification
- **Evidence Separation**: Final responses cite BOTH sources explicitly
- **Graceful Fallback**: System continues with CSV-only if API is unavailable
- **Flexible Configuration**: API URL via CLI flag or environment variable

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Command

```bash
# Full Phase 3.5 experience (Catalog API + CSV)
python main.py \
  --question "Your question here" \
  --persona CTO \
  --catalog-api-url "https://api.udacity.com/api/unified-catalog" \
  --csv-path data/NLC_Skill_Data.csv
```

### Arguments

- `--question, -q`: Seller question (required)
- `--persona, -p`: Target persona - CTO, HR, or L&D (default: CTO)
- `--catalog-api-url`: Catalog API base URL (Phase 3.5: uses real API for discovery)
- `--csv-path`: Path to CSV file (required for real data, optional for mocked data)
- `--top-k`: Number of results to retrieve (default: 5)
- `--verbose, -v`: Enable verbose output to see agent workflow

### Environment Variables

- `CATALOG_API_URL`: Catalog API base URL (alternative to `--catalog-api-url` flag)
- `USE_EMBEDDINGS=1`: Enable semantic similarity matching with sentence transformers (requires `sentence-transformers` package)

### Examples

#### Example 1: Catalog API + CSV Integration (Phase 3.5)

```bash
# Using environment variable
export CATALOG_API_URL="https://api.udacity.com/api/unified-catalog"

python main.py \
  --question "Do we have GenAI training for non-technical business leaders?" \
  --persona HR \
  --csv-path data/NLC_Skill_Data.csv \
  --verbose
```

**Two-Layer Discovery + Verification:**
- **Catalog API** discovers: "Generative AI for Business Leaders" exists
- **CSV** verifies: Skills (GenAI Strategy, AI Use Cases), Prerequisites (none), Tools (no coding required)
- **Final response** cites BOTH sources:
  - `[Catalog: cd0101, Generative AI for Business Leaders]` ← Discovery
  - `[CSV: cd0101, Course Skills Array]` ← Skill verification
  - `[CSV: cd0101, Prerequisites]` ← Depth verification

#### Example 2: Semantic Search with Aliases

```bash
python main.py --question "We need LLM training for business executives" --persona HR --csv-path data/NLC_Skill_Data.csv
```

**Semantic Features Demonstrated:**
- "LLM" automatically maps to "generative_ai" via alias matching
- Context "business executives" triggers `genai_business` intent
- System finds GenAI programs even though query uses different terminology

#### Example 3: Catalog Discovery

```bash
python main.py --question "Do we have GenAI content for non-technical roles?" --persona HR --csv-path data/NLC_Skill_Data.csv
```

**Expected Output:**
```
## Learning Programs Available

Found 3 relevant programs:

### 1. Generative AI for Business Leaders
- **Type**: Course
- **Duration**: 8.0 hours
- **Level**: Beginner
- **Summary**: Non-technical introduction to GenAI applications in business. No coding required.
- **Relevance**: 100%

### 2. GenAI for Product Managers
- **Type**: Course
- **Duration**: 10.0 hours
- **Level**: Beginner
- **Summary**: Product strategy with GenAI. Use cases, ROI analysis, vendor selection. No coding.
- **Relevance**: 67%

### 3. GenAI Prompt Engineering
- **Type**: Course
- **Duration**: 12.0 hours
- **Level**: Beginner
- **Summary**: Learn prompt engineering techniques for ChatGPT, Claude, and enterprise LLMs.
- **Relevance**: 67%

## Evidence Sources
- [Catalog: cd0101, Generative AI for Business Leaders]
- [Catalog: cd0105, GenAI for Product Managers]
- [Catalog: cd0103, GenAI Prompt Engineering]
```

#### Example 4: Recommendation

```bash
python main.py --question "Customer wants to upskill 200 Data Analysts in 6 months—what should I propose?" --persona CTO --csv-path data/NLC_Skill_Data.csv
```

**Expected Output:**
```
## Technical Assessment for CTO

**Question**: Customer wants to upskill 200 Data Analysts in 6 months—what should I propose?

## Recommended Solution

**Program**: Data Analyst Nanodegree

Master SQL, Python, and data visualization. Build projects with real datasets.

## Evaluation Against Your Requirements

### 1. Skill Coverage
**Skills taught**: SQL, Python, Pandas, Tableau, Statistics

### 2. Depth of Coverage
**Depth**: Intermediate level, 5 lessons
**Lessons**: SQL Fundamentals, Advanced SQL, Python for Data Analysis...

### 3. Hands-On Learning
**Projects**: 3 hands-on projects
- Sales Dashboard, A/B Test Analysis, Customer Segmentation

### 4. Tools & Technologies
**Tools**: PostgreSQL, Tableau, Jupyter
**Software**: PostgreSQL 12+, Python 3.8+, Tableau Desktop

### 5. Prerequisites
**Required**: Basic Excel, Basic statistics

### 6. Time to Proficiency
**Timeline**: 180.0 hours total

## Technical Readiness
This program provides production-ready skills with hands-on projects. Graduates can contribute to real projects immediately upon completion.

## Evidence Sources
- [Catalog: cd0102]
- [CSV: cd0102, Course Skills]
- [CSV: cd0102, Lessons]
- [CSV: cd0102, Projects]
- [CSV: cd0102, Tools]
- [CSV: cd0102, Prerequisites]
- [Catalog: cd0102, Duration]
```

#### Example 5: Skill Validation with Intent Detection

```bash
python main.py --question "Do you cover Python hands-on with real projects for data analysts using pandas?" --persona CTO --csv-path data/NLC_Skill_Data.csv --verbose
```

**Semantic Features Demonstrated:**
- "Python for data analysts using pandas" triggers `python_analytics` intent
- System adds preferred skills: Pandas, NumPy, Data Analysis
- Finds programs matching Python + analytics context

The `--verbose` flag shows the agent workflow:
```
============================================================
PROCESSING QUESTION: Do you cover Python hands-on with real projects?
PERSONA: CTO
============================================================

STEP 1: ROUTING...
  Task Type: skill_validation
  Retrieval Plan: catalog=True, csv=True

STEP 2: RETRIEVING EVIDENCE...
  Catalog: 3 results
  CSV: 3 details retrieved
  Comparisons: 2

STEP 3: COMPOSING RESPONSE...
  Draft 1 complete

STEP 4: CRITIC REVIEW (Attempt 1)...
  Decision: PASS
  Evidence Score: 0.90
  Completeness Score: 1.00
  Persona Fit Score: 0.70

FINAL RESPONSE APPROVED
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_router.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html
```

## Project Structure

```
sales_enablement_assistant/
├── agents/                      # Agent implementations
│   ├── router.py               # Router/orchestrator agent
│   ├── catalog_search.py       # Catalog search specialist
│   ├── csv_details.py          # CSV details specialist
│   ├── comparator.py           # Program comparison specialist
│   ├── composer.py             # Response composer
│   └── critic.py               # Response critic/validator
├── retrieval/                  # Data retrieval layer
│   ├── catalog_provider.py    # Catalog interface (mocked, Phase 1)
│   ├── catalog_api_provider.py # Real Catalog API provider (Phase 3.5)
│   ├── csv_index.py            # CSV index (mocked, Phase 1)
│   ├── csv_loader.py           # CSV loader with encoding detection (Phase 2)
│   ├── real_csv_provider.py   # Real CSV provider with skill search (Phase 2)
│   └── skill_semantics.py     # Skill semantic resolver (Phase 3)
├── schemas/                    # Pydantic schemas
│   ├── context.py             # Context and task types
│   ├── evidence.py            # Evidence types
│   ├── responses.py           # Agent response types
│   ├── aggregated.py          # Program/Course entities (Phase 2)
│   └── semantic.py            # Semantic result schemas (Phase 3)
├── config/                     # Configuration
│   ├── settings.py            # Application settings
│   └── columns.yaml           # CSV column mappings (Phase 2)
├── data/                       # Data files
│   ├── NLC_Skill_Data.csv     # Real skill data (Phase 2)
│   ├── skills_aliases.yaml    # Skill synonyms (Phase 3)
│   ├── skills_taxonomy.yaml   # Intent disambiguation rules (Phase 3)
│   └── example_questions.txt  # Sample questions
├── tests/                      # Unit tests (96 total)
│   ├── test_router.py         # Router tests
│   ├── test_csv_retrieval.py  # CSV retrieval tests
│   ├── test_critic.py         # Critic tests
│   ├── test_csv_loader.py     # CSV loader tests (Phase 2)
│   ├── test_real_csv_provider.py  # Real provider tests (Phase 2)
│   ├── test_skill_semantics.py    # Semantic unit tests (Phase 3)
│   ├── test_semantic_integration.py  # Semantic integration tests (Phase 3)
│   └── test_catalog_api_provider.py  # Catalog API tests (Phase 3.5)
├── examples/                   # Usage examples
│   └── catalog_csv_integration_example.md  # Phase 3.5 example
├── orchestrator.py             # Main orchestration logic
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── PHASE2_SUMMARY.md         # Phase 2 documentation
└── PHASE3_SUMMARY.md         # Phase 3 documentation
```

## Key Features

### Intelligent Skill Matching (Phase 3)

The semantic layer provides:
- **50+ Skill Aliases**: Natural language variations map to canonical skills
- **10+ Intent Patterns**: Context-aware disambiguation (analytics vs ML, basics vs advanced)
- **Typo Tolerance**: Fuzzy matching recovers from spelling errors
- **Query Expansion**: Automatically adds related skills based on context
- **Optional Embeddings**: Semantic similarity for advanced matching

### Real CSV Integration (Phase 2)

- **UTF-16 Support**: Handles multiple encodings and delimiters
- **Two-Tier Evidence**: Course Skills Array + Subject Array (primary) vs titles (secondary)
- **Skill Vocabulary**: 1000+ skills extracted from real curriculum data
- **Catalog Flags**: Exposes in_consumer_catalog and in_ent_catalog
- **Aggregation**: Lesson-level rows → Course entities → Program entities

### 6 Evaluation Questions

For recommendation and skill validation tasks, the system answers:
1. Do you cover this specific skill?
2. How deep is the skill coverage?
3. Is the skill taught hands-on?
4. What tools/technologies are used?
5. What prerequisites are assumed?
6. How long to reach working proficiency?

### Persona-Specific Responses

- **CTO**: Emphasizes technical depth, tools/stack, hands-on realism, production readiness
- **HR**: Focuses on role leveling, adoption, time commitment, learning outcomes
- **L&D**: Highlights learning pathways, rollout plans, cohort-based delivery, measurement

### Evidence-Based Claims

- All claims are backed by catalog or CSV evidence
- Inline citations track evidence sources
- "Assumptions & Gaps" section documents unconfirmed information
- Critic agent blocks unsupported claims

### Revision Loop

- Composer writes initial response
- Critic validates for evidence support, completeness, persona fit
- If REVISE decision, composer gets critique feedback
- Maximum 2 revisions to prevent infinite loops

## Development Phases

This system was built in three phases:

### Phase 1: Agent Architecture (Complete ✅)
- Multi-agent architecture with Router, Specialists, Composer, Critic
- Pydantic schemas for strong typing
- Orchestration with revision loop (max 2 revisions)
- Mocked data providers for rapid prototyping
- 20 unit tests

### Phase 2: Real CSV Integration (Complete ✅)
- CSV loader with UTF-16 encoding and tab delimiter support
- Column mapping configuration (columns.yaml)
- Aggregated Program and Course entity schemas
- RealCSVProvider with two-tier evidence strategy
- Skill vocabulary building from Course Skills Arrays
- 25 additional tests (45 total)

### Phase 3: Skill Semantic Layer (Complete ✅)
- Skill alias mapping (skills_aliases.yaml)
- Taxonomy-based intent disambiguation (skills_taxonomy.yaml)
- Fuzzy matching with rapidfuzz
- Optional embedding support (sentence-transformers)
- 32 additional tests (77 total)

### Phase 3.5: Unified Catalog API Integration (Complete ✅)
- CatalogAPIProvider for real API integration
- Configurable base URL (CLI flag or environment variable)
- Graceful error handling (timeout, auth errors, connection issues)
- Fallback to CSV-only if API unavailable
- Evidence separation (Catalog vs CSV)
- 19 additional tests (96 total)

**All 96 tests passing** ✅

For detailed documentation:
- **Phase 2**: See `PHASE2_SUMMARY.md`
- **Phase 3**: See `PHASE3_SUMMARY.md`
- **Phase 3.5**: See `examples/catalog_csv_integration_example.md`

## Development

### Customizing Skill Semantics

**Add new aliases** (`data/skills_aliases.yaml`):
```yaml
data_engineering:
  - Data Engineering
  - ETL
  - Data Pipelines
  - Airflow
  - Spark
```

**Add new taxonomy rules** (`data/skills_taxonomy.yaml`):
```yaml
python_data_eng:
  canonical_skill: "python"
  intent_label: "Python for Data Engineering"
  context_signals:
    - data engineering
    - ETL
    - pipelines
  preferred_skills:
    - Apache Spark
    - Airflow
```

### Customizing Personas

Edit `agents/composer.py` to customize persona-specific headers and closings.

### Adjusting Critic Rules

Edit `agents/critic.py` to change validation thresholds and criteria.

### Working with Mock Data

Edit `retrieval/catalog_provider.py` and `retrieval/csv_index.py` to add programs to the mock data (used when `--csv-path` is not provided).

## License

Proprietary - Udacity Enterprise

## Contact

For questions or issues, contact the engineering team.
