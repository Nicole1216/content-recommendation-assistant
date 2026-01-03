# Example Outputs

This document shows actual outputs from the Sales Enablement Assistant for the three example questions.

## Example 1: Catalog Discovery

**Command:**
```bash
python main.py --question "Do we have GenAI content for non-technical roles?" --persona HR
```

**Output:**
```
============================================================
FINAL RESPONSE
============================================================

## Learning Programs Available

Found 4 relevant programs:

### 1. Generative AI for Business Leaders
- **Type**: Course
- **Duration**: 8.0 hours
- **Level**: Beginner
- **Summary**: Non-technical introduction to GenAI applications in business. No coding required.
- **Relevance**: 100%

### 2. GenAI Prompt Engineering
- **Type**: Course
- **Duration**: 12.0 hours
- **Level**: Beginner
- **Summary**: Learn prompt engineering techniques for ChatGPT, Claude, and enterprise LLMs.
- **Relevance**: 100%

### 3. GenAI for Product Managers
- **Type**: Course
- **Duration**: 10.0 hours
- **Level**: Beginner
- **Summary**: Product strategy with GenAI. Use cases, ROI analysis, vendor selection. No coding.
- **Relevance**: 100%

### 4. AI Programming with Python
- **Type**: Nanodegree
- **Duration**: 120.0 hours
- **Level**: Beginner
- **Summary**: Learn Python fundamentals and AI basics. Build neural networks from scratch.
- **Relevance**: 50%

## Evidence Sources
- [Catalog: cd0101, Generative AI for Business Leaders]
- [Catalog: cd0103, GenAI Prompt Engineering]
- [Catalog: cd0105, GenAI for Product Managers]
- [Catalog: cd0000, AI Programming with Python]
```

**Analysis:**
- Correctly identified as catalog discovery task
- Found 4 programs with GenAI content
- Top 3 are specifically for non-technical audiences (no coding required)
- Ranked by relevance with fit scores
- All claims backed by catalog evidence

---

## Example 2: Recommendation for Data Analysts

**Command:**
```bash
python main.py --question "Customer wants to upskill 200 Data Analysts in 6 months—what should I propose?" --persona CTO
```

**Output:**
```
============================================================
FINAL RESPONSE
============================================================

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

**Analysis:**
- Correctly identified as recommendation task
- Extracted customer context: 200 learners, 6 months, data analyst role
- Answered all 6 evaluation questions
- Used both catalog and CSV evidence
- Tailored to CTO persona (technical readiness, production skills)
- Specific tools, prerequisites, and timeline provided

---

## Example 3: Skill Validation with Python

**Command:**
```bash
python main.py --question "Do you cover Python hands-on with real projects? What tools are used and what are the prerequisites?" --persona CTO
```

**Output:**
```
============================================================
FINAL RESPONSE
============================================================

## Technical Assessment for CTO

**Question**: Do you cover Python hands-on with real projects? What tools are used and what are the prerequisites?

## Recommended Solution

**Program**: AI Programming with Python

Learn Python fundamentals and AI basics. Build neural networks from scratch.

## Evaluation Against Your Requirements

### 1. Skill Coverage
**Skills taught**: Python, NumPy, Pandas, Neural Networks

### 2. Depth of Coverage
**Depth**: Beginner level, 5 lessons
**Lessons**: Python Basics, Data Structures, NumPy Fundamentals...

### 3. Hands-On Learning
**Projects**: 2 hands-on projects
- Image Classifier, Dog Breed Classifier

### 4. Tools & Technologies
**Tools**: Jupyter Notebook, VS Code
**Software**: Python 3.8+, Anaconda

### 5. Prerequisites
**Required**: Basic computer literacy, High school math

### 6. Time to Proficiency
**Timeline**: 120.0 hours total

## Alternative Options

**Alternative**: Data Analyst Nanodegree
- Choose if: More comprehensive depth needed, Learners have prior experience, Hands-on practice is critical

## Technical Readiness
This program provides production-ready skills with hands-on projects. Graduates can contribute to real projects immediately upon completion.

## Evidence Sources
- [Catalog: cd0000]
- [CSV: cd0000, Course Skills]
- [CSV: cd0000, Lessons]
- [CSV: cd0000, Projects]
- [CSV: cd0000, Tools]
- [CSV: cd0000, Prerequisites]
- [Catalog: cd0000, Duration]
- [Comparison: cd0000 vs cd0102]
```

**Analysis:**
- Correctly identified as skill validation task
- Directly answered the specific questions asked (hands-on, tools, prerequisites)
- Found Python program with 2 hands-on projects
- Listed specific tools (Jupyter, VS Code) and software requirements
- Listed prerequisites (basic computer literacy, high school math)
- Included comparison with alternative program
- Evidence from both catalog and CSV sources

---

## Verbose Output Example

Running with `--verbose` flag shows the agent workflow:

```bash
python main.py --question "Do you cover Python hands-on?" --persona CTO --verbose
```

Shows:
```
============================================================
PROCESSING QUESTION: Do you cover Python hands-on?
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

This shows the orchestration flow:
1. Router classifies and extracts context
2. Specialists retrieve evidence from catalog and CSV
3. Composer writes response
4. Critic validates and approves
