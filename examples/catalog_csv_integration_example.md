# Phase 3.5: Catalog API + CSV Integration Example

This example demonstrates how the Sales Enablement Assistant uses the **Catalog API for discovery** and **CSV for deep verification**.

## Architecture Flow

```
User Question
    ↓
Router Agent (classifies question)
    ↓
Catalog API Discovery (answers "Do we have X?")
    ↓
CSV Verification (answers depth, skills, tools, prerequisites)
    ↓
Composer (merges evidence from both sources)
    ↓
Critic (validates evidence from both sources)
    ↓
Final Response (cites Catalog AND CSV)
```

## Example 1: GenAI Training Discovery + Verification

### Command

```bash
export CATALOG_API_URL="https://api.udacity.com/api/unified-catalog"

python main.py \
  --question "Do we have GenAI training for non-technical business leaders?" \
  --persona HR \
  --csv-path data/NLC_Skill_Data.csv \
  --verbose
```

### What Happens

**Step 1: Router Agent**
- Task Type: `catalog_discovery`
- Extracts: "non-technical", "business leaders"

**Step 2: Catalog API Discovery** (via `CatalogAPIProvider`)
- API Call: `GET https://api.udacity.com/api/unified-catalog/search?q=GenAI+training+non-technical+business+leaders&limit=5`
- Response:
```json
{
  "results": [
    {
      "program_key": "cd0101",
      "program_title": "Generative AI for Business Leaders",
      "program_type": "Course",
      "summary": "Non-technical introduction to GenAI applications in business",
      "duration_hours": 8.0,
      "difficulty_level": "Beginner",
      "relevance_score": 0.95
    }
  ]
}
```
- **Catalog Evidence**: "We have Generative AI for Business Leaders (cd0101)"

**Step 3: CSV Deep Verification** (via `RealCSVProvider`)
- Drill into `cd0101` in CSV
- Extract:
  - **Course Skills Array**: ["GenAI Strategy", "AI Use Cases", "ROI Analysis"]
  - **Course Skills Subject Array**: ["Business Strategy", "AI Literacy"]
  - **Prerequisites**: None (beginner-friendly)
  - **Projects**: "GenAI Business Case Study"
  - **Tools**: No coding tools required
- **CSV Evidence**: "Confirmed skills, prerequisites, and hands-on requirements"

**Step 4: Composer**
- Merges evidence from Catalog AND CSV
- Writes HR-focused response

**Final Response** (with dual evidence):
```
## Learning Programs Available

Found 1 highly relevant program:

### Generative AI for Business Leaders
- **Type**: Course
- **Duration**: 8.0 hours
- **Level**: Beginner
- **Relevance**: 95%

**What You'll Learn:**
- GenAI Strategy
- AI Use Cases
- ROI Analysis

**Prerequisites:**
None - designed for non-technical leaders

**Hands-On Experience:**
Includes "GenAI Business Case Study" project

**Evidence Sources:**
- [Catalog: cd0101, Generative AI for Business Leaders] ← Discovery
- [CSV: cd0101, Course Skills Array] ← Skill verification
- [CSV: cd0101, Prerequisites] ← Depth verification
```

## Example 2: Skill Depth Validation (Python for Data Analysis)

### Command

```bash
python main.py \
  --question "Do you cover Python hands-on for data analysts? What tools and prerequisites?" \
  --persona CTO \
  --catalog-api-url "https://api.udacity.com/api/unified-catalog" \
  --csv-path data/NLC_Skill_Data.csv \
  --verbose
```

### What Happens

**Step 1: Router**
- Task Type: `skill_validation`
- Extracts: "Python", "hands-on", "data analysts"

**Step 2: Catalog Discovery**
- Finds: "Data Analyst Nanodegree" (cd0102), "Python for Data Analysis" (cd0201)
- **Catalog Evidence**: "We have 2 programs covering Python for data analysts"

**Step 3: Semantic Layer** (Phase 3)
- Query: "Python for data analysts"
- Detected Intent: `python_analytics`
- Added Skills: "Pandas", "NumPy", "Jupyter"

**Step 4: CSV Verification**
- Program: cd0102 (Data Analyst Nanodegree)
- **Course Skills Array**: ["Python", "Pandas", "NumPy", "Data Visualization", "SQL"]
- **Course Skills Subject Array**: ["Data Analysis", "Statistics"]
- **Prerequisites**: ["Basic Excel", "Basic Statistics"]
- **Projects**: ["Sales Dashboard", "A/B Test Analysis", "Customer Segmentation"]
- **Tools**: ["Python 3.8+", "Jupyter Notebooks", "PostgreSQL", "Tableau"]
- **Duration**: 180 hours

**Final Response** (CTO-focused with deep technical details):
```
## Technical Assessment for CTO

**Question**: Do you cover Python hands-on for data analysts? What tools and prerequisites?

## Programs Found

### 1. Data Analyst Nanodegree (cd0102)

**Skills Coverage** ✅
- Python (verified via Course Skills Array)
- Pandas, NumPy (verified via Course Skills Array)
- Data Visualization, SQL (verified via Course Skills Array)

**Hands-On Projects** ✅
1. Sales Dashboard - Build interactive dashboards with Tableau
2. A/B Test Analysis - Statistical analysis with Python
3. Customer Segmentation - ML clustering with scikit-learn

**Tools & Technologies** ✅
- Python 3.8+ (verified via Software Requirements)
- Jupyter Notebooks (verified via Third-Party Tools)
- PostgreSQL 12+ (verified via Software Requirements)
- Tableau Desktop (verified via Third-Party Tools)

**Prerequisites** ⚠️
- Basic Excel skills
- Basic statistics knowledge

**Time to Proficiency**
180 hours total (verified via CSV aggregation)

## Technical Readiness
Production-ready skills. Graduates can contribute to data projects immediately.

## Evidence Sources
- [Catalog: cd0102, Data Analyst Nanodegree] ← Discovery
- [CSV: cd0102, Course Skills Array] ← Skills verification
- [CSV: cd0102, Projects] ← Hands-on verification
- [CSV: cd0102, Software Requirements] ← Tools verification
- [CSV: cd0102, Prerequisites] ← Prerequisites verification
```

## Example 3: Catalog API Unavailable Fallback

### Command

```bash
# Simulate API unavailable (wrong URL or network issue)
python main.py \
  --question "GenAI training for executives" \
  --persona HR \
  --catalog-api-url "https://api.invalid-domain.com/catalog" \
  --csv-path data/NLC_Skill_Data.csv \
  --verbose
```

### What Happens

**Step 2: Catalog API Attempt**
- API Call fails (timeout/connection error)
- **Warning Issued**:
```
⚠️  Catalog API is unavailable: Connection refused
  Continuing with CSV-only search...
```

**Step 3: CSV-Only Fallback**
- System continues using CSV data
- Response includes warning:
```
⚠️ Note: Catalog API was unavailable. Results based on CSV data only.
```

**Key Benefit**: System is resilient and continues to work even if Catalog API is down.

## Evidence Separation Example

When both sources are available, evidence is clearly separated:

```
## Evidence Sources

**Catalog Evidence:**
- [Catalog: cd0101, Generative AI for Business Leaders]
  → Confirms existence of GenAI program for business leaders

**CSV Evidence:**
- [CSV: cd0101, Course Skills Array]
  → Skills: GenAI Strategy, AI Use Cases, ROI Analysis
- [CSV: cd0101, Prerequisites]
  → No coding required (beginner-friendly)
- [CSV: cd0101, Projects]
  → Hands-on: GenAI Business Case Study

**Agreements:**
✅ Program exists and covers GenAI for non-technical audience

**Gaps:**
- Catalog shows "Business Strategy" focus
- CSV confirms specific skills and tools
```

## Configuration Options

### Via CLI Flags

```bash
python main.py \
  --catalog-api-url "https://api.udacity.com/api/unified-catalog" \
  --csv-path "data/NLC_Skill_Data.csv" \
  --question "Your question here" \
  --persona CTO
```

### Via Environment Variables

```bash
export CATALOG_API_URL="https://api.udacity.com/api/unified-catalog"

python main.py \
  --csv-path "data/NLC_Skill_Data.csv" \
  --question "Your question here" \
  --persona CTO
```

### Mixed Mode (Phase 3.5 Default)

- **With Catalog API**: Discovery layer (existence, high-level coverage)
- **With CSV**: Verification layer (skills, tools, prerequisites, depth)
- **Both Together**: Best experience - fast discovery + deep validation

### Backward Compatibility

- **No Catalog API**: Uses mock catalog (Phase 1 behavior)
- **No CSV**: Uses catalog only (discovery only)
- **Both**: Full Phase 3.5 experience

## Key Principles

1. **Catalog for "Do we have X?"** - Fast discovery
2. **CSV for "How deep? What tools?"** - Detailed verification
3. **Evidence Separation** - Always cite both sources
4. **Graceful Degradation** - System works even if one source fails
5. **No Hallucination** - Skills ONLY from Course Skills Array, NOT inferred from text
