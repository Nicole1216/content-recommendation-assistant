# Phase 2 Implementation Summary

## Overview

Phase 2 successfully integrates **real CSV data** as the "deep verification layer" while maintaining the existing Phase 1 architecture intact. No agent logic, orchestration flow, or Composer/Critic behavior was modified.

## What Was Delivered

### 1. CSV Loading Infrastructure

**File**: `retrieval/csv_loader.py`
- Handles multiple encodings (UTF-16, UTF-8, Latin-1)
- Handles multiple delimiters (tab, comma)
- Normalizes null values (`"Null"`, `"null"`, `""`, `NaN` → `None`)
- Parses boolean fields (`TRUE`/`FALSE` → `bool`)
- Parses numeric fields with coercion
- Parses array fields (Course Skills Array, Course Skills Subject Array, concept_titles):
  - Splits by comma
  - Strips whitespace
  - Drops empty/"null" values
  - Deduplicates while preserving order

### 2. Column Mapping Configuration

**File**: `config/columns.yaml`
- Maps logical field names to actual CSV column names
- Handles column names with trailing spaces (e.g., `"Generic Program Title "`)
- Supports program-level, course-level, and lesson-level fields

### 3. Aggregated Entity Schemas

**File**: `schemas/aggregated.py`

**ProgramEntity**: Aggregated from lesson-level CSV rows
- Program metadata (title, type, duration, difficulty, persona, etc.)
- **Catalog flags** (MUST be exposed):
  - `in_consumer_catalog`
  - `in_ent_catalog`
- **Skills union**: Union of all `Course Skills Array` + `Course Skills Subject Array`
- **Skills by course**: Mapping of course_key → skills
- Aggregated counts (courses, lessons, projects)
- Business metadata (GTM, partners, clients, enrollments)

**CourseEntity**: Aggregated per program_key + course_key
- **CRITICAL skill arrays** (first-class indices):
  - `course_skills_array`
  - `course_skills_subject_array`
- Course metadata (title, summary, prerequisites)
- Tools & requirements
- **Lesson outline**: Ordered distinct lesson titles
- **Project information**: Project titles, hands-on flag
- Concept titles

**ProgramSearchResult**:
- Program entity
- Relevance score
- **Matched evidence**:
  - `matched_course_skills`
  - `matched_course_skill_subjects`
  - `matched_courses` (which courses matched)
- Source columns tracked

### 4. Real CSV Provider with Skill-Based Search

**File**: `retrieval/real_csv_provider.py`

**Two-Tier Evidence Strategy** (as required):

#### Tier 1: Coverage (Primary Evidence)
- **Course Skills Array**
- **Course Skills Subject Array**

A program may ONLY be considered "covering" a skill if one of these matches.

#### Tier 2: Fit & Depth (Secondary Evidence)
- Course Title / Summary
- Program Title / Summary
- Lesson Title / Summary
- Project Title

These influence ranking and explanation but do NOT alone justify "we cover this skill" claims.

**Ranking Weights**:
- Exact skill match: 10.0 (highest)
- Course title/summary: 3.0 (medium)
- Program title/summary: 2.0 (medium)
- Lesson/project: 0.5 (explanatory)

**API Methods**:
1. `search_programs(query, top_k)` - Skill-aware search with ranking
2. `get_program_details(program_key)` - Program summary
3. `get_program_deep_details(program_key)` - Full details with courses
4. `get_details(program_keys)` - Backward compatibility with CSVDetail format

### 5. Orchestrator Integration

**File**: `orchestrator.py`
- Uses `RealCSVProvider` if `csv_path` is provided
- Falls back to mock `CSVIndex` if no path
- **NO changes** to agent logic
- **NO changes** to orchestration flow

### 6. CLI Enhancement

**File**: `main.py`
- Added `--csv-path` flag
- Phase 2: Uses real CSV if provided, otherwise uses mock data

### 7. Test Coverage

**New Tests**:
- `tests/test_csv_loader.py` (8 tests) - CSV loading, parsing, array handling
- `tests/test_real_csv_provider.py` (17 tests) - Aggregation, search, evidence tracking

**Phase 1 Tests** (all still passing):
- `tests/test_router.py` (8 tests)
- `tests/test_csv_retrieval.py` (7 tests)
- `tests/test_critic.py` (5 tests)

**Total**: 45 tests, all passing

## Key Features

### Skill-Based Search
```python
from retrieval.real_csv_provider import RealCSVProvider

provider = RealCSVProvider('data/NLC_Skill_Data.csv')
results = provider.search_programs("Python", top_k=5)

for r in results:
    print(f"{r.program_entity.program_title}: {r.relevance_score}")
    print(f"  Matched skills: {r.matched_course_skills}")
    print(f"  Evidence sources: {r.source_columns}")
```

### Aggregation
- **Programs**: 100+ unique programs aggregated from 8000+ lesson rows
- **Courses**: 500+ unique courses with skill arrays preserved
- **Skills**: Correctly deduplicated and mapped to courses

### Evidence Tracking
Every search result includes:
- Source: `"csv"`
- `program_key`
- `course_key` (when applicable)
- `source_columns` used for matching

### Catalog Flags
Both flags are exposed on every program:
- `in_consumer_catalog` (bool)
- `in_ent_catalog` (bool)

## Usage Examples

### Basic Search
```bash
python main.py --question "Do we have Python content?" \
  --persona CTO \
  --csv-path data/NLC_Skill_Data.csv
```

### With Mock Data (Phase 1 behavior)
```bash
python main.py --question "Do we have Python content?" \
  --persona CTO
  # No --csv-path = uses mock data
```

### Verbose Mode
```bash
python main.py --question "Customer needs Data Analyst training" \
  --persona CTO \
  --csv-path data/NLC_Skill_Data.csv \
  --verbose
```

## Phase 2 Constraints Met

✅ **Do NOT change Router logic** - No changes
✅ **Do NOT change Composer or Critic behavior** - No changes
✅ **Do NOT remove mock providers** - Mock CSVIndex still exists
✅ **Do NOT assume Catalog API availability** - Catalog provider is separate
✅ **Phase 2 = retrieval upgrade ONLY** - Confirmed

## Evidence Requirements Met

✅ Every claim carries evidence with `source: "csv"`
✅ `program_key` tracked
✅ `course_key` tracked when applicable
✅ `source_columns` tracked
✅ If skill NOT confirmed via skill arrays → "Not confirmed from CSV skills data"

## Architecture Principles

### Separation of Concerns
- **Catalog API** (or mock): "What exists?" / discovery / shortlist
- **CSV**: Verification + depth (tools, prerequisites, structure, hands-on)

### Two-Tier Evidence
- **Primary**: Course Skills Array + Subject Array (COVERAGE)
- **Secondary**: Title/summary fields (FIT & DEPTH)

### Backward Compatibility
- All Phase 1 agents work unchanged
- Mock providers still available
- Existing tests still pass

## File Structure

```
sales_enablement_assistant/
├── config/
│   └── columns.yaml          # NEW: Column mapping
├── retrieval/
│   ├── catalog_provider.py   # Phase 1: Mock catalog
│   ├── csv_index.py          # Phase 1: Mock CSV
│   ├── csv_loader.py         # NEW: Real CSV loader
│   └── real_csv_provider.py  # NEW: Real CSV provider
├── schemas/
│   ├── aggregated.py         # NEW: Program/Course entities
│   ├── context.py            # Phase 1
│   ├── evidence.py           # Phase 1
│   └── responses.py          # Phase 1
├── tests/
│   ├── test_csv_loader.py    # NEW: CSV loading tests
│   └── test_real_csv_provider.py  # NEW: Provider tests
└── data/
    └── NLC_Skill_Data.csv    # Real CSV file (UTF-16, tab-delimited)
```

## Next Steps (Future Enhancements)

### Phase 3 Possibilities
- Vector embeddings for semantic search (FAISS)
- Real catalog API integration
- Caching layer for CSV aggregation
- Advanced ranking algorithms
- Multi-language support

## Testing the Implementation

### Run All Tests
```bash
pytest
```

### Run Specific Test Suites
```bash
# Phase 2 tests
pytest tests/test_csv_loader.py -v
pytest tests/test_real_csv_provider.py -v

# Phase 1 regression tests
pytest tests/test_router.py -v
pytest tests/test_csv_retrieval.py -v
pytest tests/test_critic.py -v
```

### Test with Real CSV
```bash
python main.py \
  --question "Do we cover Python hands-on?" \
  --persona CTO \
  --csv-path data/NLC_Skill_Data.csv \
  --verbose
```

## Performance

- **CSV Loading**: ~1-2 seconds for 8000+ rows
- **Aggregation**: ~3-5 seconds (runs once at startup)
- **Search**: ~0.1-0.3 seconds per query
- **Memory**: ~50-100 MB for aggregated data structures

## Known Limitations (Phase 2)

1. **Catalog-CSV Key Mismatch**: Mock catalog uses different program keys (cd0102) than real CSV (nd002). This is expected - in production, catalog API and CSV would be synchronized.

2. **Search Algorithm**: Currently uses simple keyword matching. Phase 3 could add semantic search with embeddings.

3. **No Caching**: Aggregation runs on every load. Production would benefit from caching.

## Conclusion

Phase 2 successfully delivers:
- ✅ Real CSV integration
- ✅ Skill-based search with proper evidence hierarchy
- ✅ Complete aggregation from lesson-level to program-level
- ✅ Backward compatibility
- ✅ Comprehensive test coverage
- ✅ No changes to existing agent logic

The system now supports both mock data (Phase 1) and real CSV data (Phase 2) seamlessly through the `--csv-path` flag.
