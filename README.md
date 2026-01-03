# Sales Enablement Assistant

An agentic AI system for Udacity Enterprise sellers that provides intelligent, evidence-based responses to customer questions, tailored to specific stakeholder personas (CTO, HR, L&D).

## Overview

The Sales Enablement Assistant helps sellers quickly answer questions like:
- "Do we have GenAI content for non-technical roles?"
- "Customer wants to upskill 200 Data Analysts in 6 months—what should I propose?"
- "Do you cover Python hands-on with real projects?"

It retrieves information from two sources (catalog and CSV details), validates claims, and generates persona-specific responses.

## Architecture

The system implements a multi-agent architecture:

1. **Router Agent**: Classifies questions into task types (discovery, recommendation, skill validation) and extracts customer context
2. **Specialist Agents**:
   - CatalogSearch: Searches and ranks programs from catalog
   - CSVDetails: Retrieves detailed curriculum information
   - Comparator: Compares programs across 6 evaluation dimensions
3. **Composer Agent**: Writes final seller-facing responses tailored to persona
4. **Critic Agent**: Validates responses for evidence support, completeness, and persona fit

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
python main.py --question "Your question here" --persona CTO
```

### Arguments

- `--question, -q`: Seller question (required)
- `--persona, -p`: Target persona - CTO, HR, or L&D (default: CTO)
- `--csv-path`: Path to CSV file (optional in Phase 1)
- `--top-k`: Number of results to retrieve (default: 5)
- `--verbose, -v`: Enable verbose output to see agent workflow

### Examples

#### Example 1: Catalog Discovery

```bash
python main.py --question "Do we have GenAI content for non-technical roles?" --persona HR
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

#### Example 2: Recommendation

```bash
python main.py --question "Customer wants to upskill 200 Data Analysts in 6 months—what should I propose?" --persona CTO
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

#### Example 3: Skill Validation

```bash
python main.py --question "Do you cover Python hands-on with real projects? What tools are used and what are the prerequisites?" --persona CTO --verbose
```

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
├── agents/                 # Agent implementations
│   ├── router.py          # Router/orchestrator agent
│   ├── catalog_search.py  # Catalog search specialist
│   ├── csv_details.py     # CSV details specialist
│   ├── comparator.py      # Program comparison specialist
│   ├── composer.py        # Response composer
│   └── critic.py          # Response critic/validator
├── retrieval/             # Data retrieval layer
│   ├── catalog_provider.py  # Catalog interface (mocked)
│   └── csv_index.py          # CSV index (mocked)
├── schemas/               # Pydantic schemas
│   ├── context.py        # Context and task types
│   ├── evidence.py       # Evidence types
│   └── responses.py      # Agent response types
├── config/               # Configuration
│   └── settings.py      # Application settings
├── data/                # Sample data
│   └── example_questions.txt
├── tests/               # Unit tests
│   ├── test_router.py
│   ├── test_csv_retrieval.py
│   └── test_critic.py
├── orchestrator.py      # Main orchestration logic
├── main.py             # CLI entry point
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Key Features

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

## Phase 1 Limitations

This is Phase 1 implementation with mocked data:
- Catalog search uses simple keyword matching (not real API)
- CSV data is hardcoded in memory (not real file parsing)
- Retrieval uses basic text matching (no vector search)

Phase 2 will integrate:
- Real catalog API
- Real CSV file parsing
- Vector embeddings for semantic search
- More sophisticated retrieval strategies

## Development

### Adding New Mock Programs

Edit `retrieval/catalog_provider.py` and `retrieval/csv_index.py` to add programs to the mock data.

### Customizing Personas

Edit `agents/composer.py` to customize persona-specific headers and closings.

### Adjusting Critic Rules

Edit `agents/critic.py` to change validation thresholds and criteria.

## License

Proprietary - Udacity Enterprise

## Contact

For questions or issues, contact the engineering team.
