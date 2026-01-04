# Phase 3: Skill Semantic Layer

## Overview

Phase 3 adds a **Skill Semantic Resolver** layer that significantly improves the seller query experience by:

1. **Alias Mapping**: Maps synonyms to canonical skills (e.g., "LLM" → "generative_ai")
2. **Taxonomy Disambiguation**: Detects skill intents via context (e.g., "Python for analysts" vs "Python for ML engineers")
3. **Fuzzy Matching**: Recovers from typos and variations (e.g., "Pyton" → "Python")
4. **Optional Embeddings**: Semantic similarity matching (feature flag)

## Key Improvements

### Before Phase 3
- Exact keyword matching only
- "LLM" wouldn't find "Generative AI" programs
- Typos like "Pyton" would fail completely
- No context understanding

### After Phase 3
- **Synonym awareness**: "LLM", "GenAI", "Prompt Engineering" all map to generative_ai
- **Intent detection**: "Python for data analysts" → adds pandas, numpy, jupyter signals
- **Typo tolerance**: "Pyton" → finds "Python" via fuzzy matching
- **Contextual understanding**: "SQL optimization" → detects advanced SQL intent

## Architecture

### Components Added

1. **Skill Semantic Resolver** (`retrieval/skill_semantics.py`)
   - Resolves queries through 4 layers: alias → taxonomy → fuzzy → embeddings
   - Returns `SkillSemanticResult` with normalized skills, intents, and expansions

2. **Data Files**
   - `data/skills_aliases.yaml`: Synonym mappings
   - `data/skills_taxonomy.yaml`: Intent disambiguation rules

3. **Schemas** (`schemas/semantic.py`)
   - `SkillCandidate`: Individual skill match with score and source
   - `SkillSemanticResult`: Complete resolution with explanations

4. **Integration** (`retrieval/real_csv_provider.py`)
   - Builds skill vocabulary from CSV at load time
   - Uses semantic resolver before search
   - Adds normalized skills + expansions to search terms

## Usage Examples

### Example 1: Alias Mapping

```bash
# Query using "LLM" instead of "Generative AI"
python main.py --question "We need LLM training for executives" \
  --persona HR \
  --csv-path data/NLC_Skill_Data.csv
```

**Result**: Finds GenAI programs because "LLM" maps to "generative_ai"

### Example 2: Intent Disambiguation

```bash
# Query with analytics context
python main.py --question "Python for data analysts using pandas and jupyter" \
  --persona CTO \
  --csv-path data/NLC_Skill_Data.csv
```

**Result**:
- Detects `python_analytics` intent
- Adds preferred skills: Pandas, NumPy, Jupyter
- Finds Python + Data Analysis programs

### Example 3: Fuzzy Matching

```bash
# Query with typo
python main.py --question "Tablea visualization training" \
  --persona L&D \
  --csv-path data/NLC_Skill_Data.csv
```

**Result**: "Tablea" fuzzy matches to "Tableau" and finds visualization programs

### Example 4: Combined Resolution

```bash
# Multiple features working together
python main.py --question "LLM prompt engineering for developers" \
  --persona CTO \
  --csv-path data/NLC_Skill_Data.csv
```

**Result**:
- "LLM" → generative_ai (alias)
- "prompt engineering" → generative_ai (alias)
- Context "for developers" → genai_technical intent (taxonomy)
- Adds preferred skills: Prompt Engineering, API Integration

## Skill Aliasesyaml
generative_ai:
  - GenAI
  - Gen AI
  - LLM
  - Large Language Model
  - GPT
  - ChatGPT
  - Prompt Engineering
  - AI Literacy

python_analytics:
  - Python for Data Analysis
  - Pandas
  - NumPy
  - Jupyter

sql_advanced:
  - Advanced SQL
  - SQL Optimization
  - Window Functions
  - CTEs
  - Query Optimization
```

## Taxonomy Examples

```yaml
python_analytics:
  canonical_skill: "python"
  intent_label: "Python for Data Analytics"
  context_signals:
    - analyst
    - analytics
    - pandas
    - numpy
    - jupyter
  preferred_skills:
    - Pandas
    - NumPy
    - Data Analysis

sql_advanced:
  canonical_skill: "sql"
  intent_label: "Advanced SQL & Optimization"
  context_signals:
    - optimization
    - window functions
    - CTE
    - execution plan
  preferred_skills:
    - Query Optimization
    - Window Functions
```

## API

### SkillSemanticResolver

```python
from retrieval.skill_semantics import SkillSemanticResolver

# Initialize
resolver = SkillSemanticResolver(skill_vocabulary=["Python", "SQL", ...])

# Resolve query
result = resolver.resolve(
    query="LLM training",
    context="for business executives non-technical"
)

# Results
print(result.normalized_skills)      # ['generative_ai']
print(result.skill_intents)          # ['genai_business']
print(result.query_expansions)       # ['GenAI Strategy', 'AI Use Cases']
print(result.confidence)             # 1.0
print(result.why)                    # "Alias match: 'generative_ai'; Intent: GenAI for Business Leaders"
```

### Semantic Result Schema

```python
class SkillSemanticResult:
    normalized_skills: list[str]       # Canonical skill names
    skill_intents: list[str]           # Detected intents (e.g., python_analytics)
    query_expansions: list[str]        # Additional terms to improve search
    confidence: float                  # 0.0-1.0
    why: str                           # Explanation of resolution
    candidates: list[SkillCandidate]   # All matches considered
    original_query: str                # Original input
```

## Resolution Pipeline

```
User Query: "LLM for data analysts"
    ↓
1. Alias Matching
   "LLM" → generative_ai (score: 1.0)
   "data" → data_analysis (score: 0.95)
    ↓
2. Taxonomy Matching
   Context: "for data analysts"
   Detected: data_analysis_basic intent
   Expansions: [Excel, Statistics]
    ↓
3. Fuzzy Matching
   (skipped - strong alias matches exist)
    ↓
4. Embedding Matching (if USE_EMBEDDINGS=1)
   (skipped - not enabled)
    ↓
Result:
   normalized_skills: [generative_ai, data_analysis]
   skill_intents: [data_analysis_basic]
   query_expansions: [Excel, Statistics]
   confidence: 1.0
```

## Optional Embeddings

Enable semantic similarity with sentence transformers:

```bash
# Install optional dependency
pip install sentence-transformers

# Enable embeddings
export USE_EMBEDDINGS=1

# Run
python main.py --question "natural language processing" \
  --persona CTO \
  --csv-path data/NLC_Skill_Data.csv
```

**How it works**:
- Uses `all-MiniLM-L6-v2` model
- Embeds query and skill vocabulary
- Finds nearest neighbors via cosine similarity
- Fallback: works without embeddings

## Testing

### Run Phase 3 Tests

```bash
# Semantic resolver unit tests (24 tests)
pytest tests/test_skill_semantics.py -v

# Integration tests (8 tests)
pytest tests/test_semantic_integration.py -v

# All tests (77 total)
pytest
```

### Test Coverage

**Alias Tests**:
- GenAI/LLM/Prompt Engineering mappings
- Python variant mappings
- SQL variant mappings

**Taxonomy Tests**:
- Python analytics vs ML disambiguation
- SQL basics vs advanced disambiguation
- GenAI business vs technical disambiguation

**Fuzzy Tests**:
- Typo recovery (Pyton → Python)
- Partial matches (Tablea → Tableau)
- Variation matching

**Integration Tests**:
- End-to-end search with aliases
- Taxonomy improving relevance
- Skill vocabulary building

## Configuration

### Adding New Aliases

Edit `data/skills_aliases.yaml`:

```yaml
# Add new skill group
data_engineering:
  - Data Engineering
  - ETL
  - Data Pipelines
  - Airflow
  - Spark
```

### Adding New Taxonomy

Edit `data/skills_taxonomy.yaml`:

```yaml
python_data_eng:
  canonical_skill: "python"
  intent_label: "Python for Data Engineering"
  context_signals:
    - data engineering
    - ETL
    - pipelines
    - airflow
    - spark
  required_skills:
    - Python
    - Data Engineering
  preferred_skills:
    - Apache Spark
    - Airflow
```

## Performance

- **Initialization**: ~1-2 seconds (loads aliases, taxonomy, builds vocabulary)
- **Resolution**: ~5-20ms per query
  - Alias: ~1ms
  - Taxonomy: ~2ms
  - Fuzzy: ~10ms (depends on vocabulary size)
  - Embeddings: ~50-100ms (if enabled)
- **Memory**: +5-10 MB for vocabulary and embeddings

## Backward Compatibility

- ✅ All Phase 1 & 2 tests still pass (45 tests)
- ✅ Semantic layer is transparent - improves search without changing agent logic
- ✅ Works without embeddings (optional feature)
- ✅ Falls back gracefully if data files missing

## Limitations

1. **Alias Coverage**: Only as good as the alias mappings defined
2. **Taxonomy Scope**: Intents must be pre-defined
3. **Fuzzy Threshold**: May miss very different spellings
4. **Case Sensitivity**: Handles automatically but worth noting
5. **Context Window**: Uses full question for context, may be noisy

## Future Enhancements

### Phase 4 Possibilities
- **Dynamic alias learning**: Learn aliases from usage patterns
- **Multi-language support**: Aliases in different languages
- **Hierarchical taxonomy**: Skill ontology with parent/child relationships
- **Confidence tuning**: ML-based confidence scoring
- **Query rewriting**: Generate alternative queries for better coverage

## Files Changed/Added

### New Files
- `data/skills_aliases.yaml` - Synonym mappings
- `data/skills_taxonomy.yaml` - Intent disambiguation rules
- `schemas/semantic.py` - Semantic result schemas
- `retrieval/skill_semantics.py` - Semantic resolver implementation
- `tests/test_skill_semantics.py` - Unit tests (24 tests)
- `tests/test_semantic_integration.py` - Integration tests (8 tests)

### Modified Files
- `retrieval/real_csv_provider.py` - Added semantic resolution
- `requirements.txt` - Added rapidfuzz dependency

## Dependencies

**Required**:
- `rapidfuzz>=3.0.0` - Fuzzy string matching

**Optional**:
- `sentence-transformers>=2.2.0` - Embedding-based matching

## Summary

Phase 3 delivers a production-ready semantic layer that:
- ✅ Maps 50+ skill aliases to canonical forms
- ✅ Disambiguates 10+ skill intents via taxonomy
- ✅ Recovers from typos with fuzzy matching
- ✅ Optionally uses embeddings for semantic similarity
- ✅ Integrates seamlessly with existing architecture
- ✅ Passes 77 total tests (32 new for Phase 3)
- ✅ Improves seller query experience without changing agents

**Impact**: Sellers can now use natural language (LLM, GenAI, prompt engineering) instead of exact keywords, and the system intelligently understands intent and finds relevant programs.
