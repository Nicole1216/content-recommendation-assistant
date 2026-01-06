"""Real CSV provider with skill-based search and aggregation."""

import logging
import pandas as pd
from typing import Optional
from collections import defaultdict
from retrieval.csv_loader import CSVLoader
from retrieval.skill_semantics import SkillSemanticResolver
from retrieval.embeddings_manager import EmbeddingsManager
from schemas.aggregated import ProgramEntity, CourseEntity, ProgramSearchResult
from schemas.evidence import CSVDetail

logger = logging.getLogger(__name__)


class RealCSVProvider:
    """Real CSV provider for Phase 2 & 3."""

    # Role-to-skills mapping for career transition queries
    ROLE_SKILLS_MAP = {
        # Data roles
        "data scientist": ["machine learning", "python", "statistics", "data analysis", "sql", "deep learning", "data visualization", "pandas", "numpy", "scikit-learn"],
        "data analysts": ["sql", "data analysis", "excel", "data visualization", "python", "statistics", "tableau", "power bi"],
        "data analyst": ["sql", "data analysis", "excel", "data visualization", "python", "statistics", "tableau", "power bi"],
        "data engineer": ["sql", "python", "etl", "data pipelines", "spark", "airflow", "data warehousing", "cloud"],
        "machine learning engineer": ["machine learning", "deep learning", "python", "tensorflow", "pytorch", "mlops", "model deployment"],
        "ml engineer": ["machine learning", "deep learning", "python", "tensorflow", "pytorch", "mlops", "model deployment"],
        "ai engineer": ["artificial intelligence", "machine learning", "deep learning", "nlp", "computer vision", "python", "generative ai"],

        # Software engineering roles
        "software engineer": ["python", "java", "javascript", "software development", "algorithms", "data structures", "git"],
        "software developer": ["python", "java", "javascript", "software development", "algorithms", "data structures", "git"],
        "frontend developer": ["javascript", "html", "css", "react", "web development", "typescript", "frontend"],
        "front-end developer": ["javascript", "html", "css", "react", "web development", "typescript", "frontend"],
        "backend developer": ["python", "java", "sql", "api", "backend", "databases", "node.js"],
        "full stack developer": ["javascript", "python", "html", "css", "react", "sql", "web development", "api"],
        "fullstack developer": ["javascript", "python", "html", "css", "react", "sql", "web development", "api"],

        # Cloud & DevOps roles
        "cloud engineer": ["aws", "azure", "cloud computing", "kubernetes", "docker", "infrastructure", "terraform"],
        "devops engineer": ["ci/cd", "docker", "kubernetes", "aws", "linux", "automation", "infrastructure as code"],
        "site reliability engineer": ["sre", "monitoring", "kubernetes", "linux", "automation", "incident management"],

        # Security roles
        "cybersecurity analyst": ["cybersecurity", "security", "network security", "threat detection", "incident response"],
        "security engineer": ["cybersecurity", "security architecture", "penetration testing", "security"],

        # Management roles
        "product manager": ["product management", "agile", "user research", "roadmap", "stakeholder management"],
        "project manager": ["project management", "agile", "scrum", "stakeholder management", "risk management"],
        "engineering manager": ["leadership", "management", "agile", "team building", "technical leadership"],

        # AI/GenAI roles
        "prompt engineer": ["prompt engineering", "generative ai", "llm", "ai", "natural language processing"],
        "ai architect": ["artificial intelligence", "machine learning", "system design", "architecture", "mlops"],
    }

    def __init__(self, csv_path: str, openai_api_key: Optional[str] = None):
        """
        Initialize with real CSV file.

        Args:
            csv_path: Path to CSV file
            openai_api_key: Optional OpenAI API key for embeddings
        """
        self.csv_path = csv_path
        self.loader = CSVLoader()
        self.df: Optional[pd.DataFrame] = None
        self.programs: dict[str, ProgramEntity] = {}
        self.courses: dict[str, CourseEntity] = {}
        self.skill_vocabulary: list[str] = []
        self.semantic_resolver: Optional[SkillSemanticResolver] = None
        self.embeddings_manager: Optional[EmbeddingsManager] = None
        self._openai_api_key = openai_api_key

        # Load and aggregate
        self._load()

    def _load(self):
        """Load CSV and aggregate into entities."""
        # Load CSV with cleaning
        self.df = self.loader.load_csv(self.csv_path)

        # Aggregate courses
        self._aggregate_courses()

        # Aggregate programs
        self._aggregate_programs()

        # Build skill vocabulary (Phase 3)
        self._build_skill_vocabulary()

        # Initialize semantic resolver (Phase 3)
        self.semantic_resolver = SkillSemanticResolver(
            skill_vocabulary=self.skill_vocabulary
        )

        # Initialize embeddings manager for semantic search
        self._initialize_embeddings()

    def _get_col(self, category: str, field: str) -> Optional[str]:
        """Get column name helper."""
        return self.loader.get_column_name(category, field)

    def _aggregate_courses(self):
        """Aggregate courses from lesson-level rows."""
        # Group by program_key + course_key
        program_key_col = self._get_col('program', 'program_key')
        course_key_col = self._get_col('course', 'course_key')

        if not program_key_col or not course_key_col:
            return

        # Drop rows without course key
        df_with_course = self.df[self.df[course_key_col].notna()].copy()

        for (prog_key, course_key), group in df_with_course.groupby([program_key_col, course_key_col]):
            # Take first non-null for course-level fields
            course_entity = CourseEntity(
                program_key=str(prog_key),
                course_key=str(course_key),
                course_title=self._first_non_null(group, 'course', 'course_title') or "",
                course_summary=self._first_non_null(group, 'course', 'course_summary'),
                course_duration_hours=self._first_non_null(group, 'course', 'course_duration_hours'),
            )

            # Parse skill arrays (CRITICAL)
            skills_array_col = self._get_col('course', 'course_skills_array')
            skills_subject_col = self._get_col('course', 'course_skills_subject_array')

            if skills_array_col:
                all_skills = []
                for val in group[skills_array_col].dropna():
                    if isinstance(val, list):
                        all_skills.extend(val)
                course_entity.course_skills_array = self._dedupe_preserve_order(all_skills)

            if skills_subject_col:
                all_subjects = []
                for val in group[skills_subject_col].dropna():
                    if isinstance(val, list):
                        all_subjects.extend(val)
                course_entity.course_skills_subject_array = self._dedupe_preserve_order(all_subjects)

            # Parse skill domains
            skill_domains_col = self._get_col('course', 'skill_domains')
            if skill_domains_col:
                all_domains = []
                for val in group[skill_domains_col].dropna():
                    if isinstance(val, list):
                        all_domains.extend(val)
                course_entity.skill_domains = self._dedupe_preserve_order(all_domains)

            # Aggregate other array fields
            course_entity.course_prereq_skills = self._merge_array_field(group, 'course', 'course_prereq_skills')
            course_entity.third_party_tools = self._merge_array_field(group, 'course', 'third_party_tools')
            course_entity.software_requirements = self._merge_array_field(group, 'course', 'software_requirements')
            course_entity.hardware_requirements = self._merge_array_field(group, 'course', 'hardware_requirements')

            # Lesson outline (ordered, distinct)
            lesson_title_col = self._get_col('lesson', 'lesson_title')
            if lesson_title_col:
                lesson_titles = []
                for title in group[lesson_title_col].dropna():
                    if title and title not in lesson_titles:
                        lesson_titles.append(str(title))
                course_entity.lesson_outline = lesson_titles
                course_entity.lesson_count = len(lesson_titles)

            # Projects
            project_title_col = self._get_col('lesson', 'project_title')
            if project_title_col:
                project_titles = []
                for title in group[project_title_col].dropna():
                    if title and title not in project_titles:
                        project_titles.append(str(title))
                course_entity.project_titles = project_titles
                course_entity.project_count = len(project_titles)
                course_entity.hands_on = len(project_titles) > 0

            # Concepts
            concept_col = self._get_col('lesson', 'concept_titles')
            if concept_col:
                course_entity.concept_titles = self._merge_array_field(group, 'lesson', 'concept_titles')

            # Store
            entity_key = f"{prog_key}:{course_key}"
            self.courses[entity_key] = course_entity

    def _aggregate_programs(self):
        """Aggregate programs from lesson-level rows."""
        program_key_col = self._get_col('program', 'program_key')
        if not program_key_col:
            return

        for prog_key, group in self.df.groupby(program_key_col):
            prog_entity = ProgramEntity(
                program_key=str(prog_key),
                program_title=self._first_non_null(group, 'program', 'program_title') or "",
                program_type=self._first_non_null(group, 'program', 'program_type'),
                program_summary=self._first_non_null(group, 'program', 'program_summary'),
                program_duration_hours=self._first_non_null(group, 'program', 'program_duration_hours'),
                difficulty_level=self._first_non_null(group, 'program', 'difficulty_level'),
                primary_school=self._first_non_null(group, 'program', 'primary_school'),
                persona=self._first_non_null(group, 'program', 'persona'),
                program_url=self._first_non_null(group, 'program', 'program_url'),
                program_category=self._first_non_null(group, 'program', 'program_category'),
                syllabus_overview=self._first_non_null(group, 'program', 'syllabus_overview'),
            )

            # Catalog flags
            in_consumer_col = self._get_col('program', 'in_consumer_catalog')
            in_ent_col = self._get_col('program', 'in_ent_catalog')

            if in_consumer_col:
                val = self._first_non_null_raw(group, in_consumer_col)
                prog_entity.in_consumer_catalog = bool(val) if val is not None else False

            if in_ent_col:
                val = self._first_non_null_raw(group, in_ent_col)
                prog_entity.in_ent_catalog = bool(val) if val is not None else False

            # Numeric fields
            enrollments_col = self._get_col('program', 'total_active_enrollments')
            if enrollments_col:
                val = self._first_non_null_raw(group, enrollments_col)
                if pd.notna(val):
                    prog_entity.total_active_enrollments = int(val)

            # Array fields
            prog_entity.program_prereq_skills = self._merge_array_field(group, 'program', 'program_prereq_skills')
            prog_entity.gtm_array = self._merge_array_field(group, 'program', 'gtm_array')
            prog_entity.partners = self._merge_array_field(group, 'program', 'partners')
            prog_entity.clients = self._merge_array_field(group, 'program', 'clients')

            # Version
            prog_entity.version = self._first_non_null(group, 'program', 'version')
            prog_entity.version_released_at = self._first_non_null(group, 'program', 'version_released_at')

            # Aggregate courses and skills
            course_key_col = self._get_col('course', 'course_key')
            if course_key_col:
                distinct_courses = group[course_key_col].dropna().unique().tolist()
                prog_entity.courses = [str(c) for c in distinct_courses]
                prog_entity.course_count = len(prog_entity.courses)

            # Skills union from courses
            skills_union = set()
            skill_domains_union = set()
            skills_by_course = {}

            for course_key in prog_entity.courses:
                entity_key = f"{prog_key}:{course_key}"
                if entity_key in self.courses:
                    course_entity = self.courses[entity_key]
                    course_skills = course_entity.course_skills_array + course_entity.course_skills_subject_array
                    skills_union.update(course_skills)
                    skill_domains_union.update(course_entity.skill_domains)
                    if course_skills:
                        skills_by_course[course_key] = course_skills

            prog_entity.skills_union = list(skills_union)
            prog_entity.skill_domains = list(skill_domains_union)
            prog_entity.skills_by_course = skills_by_course

            # Lesson and project counts
            lesson_title_col = self._get_col('lesson', 'lesson_title')
            if lesson_title_col:
                prog_entity.lesson_count = group[lesson_title_col].notna().sum()

            project_title_col = self._get_col('lesson', 'project_title')
            if project_title_col:
                prog_entity.project_count = group[project_title_col].notna().sum()

            # Store
            self.programs[str(prog_key)] = prog_entity

    def _first_non_null(self, group: pd.DataFrame, category: str, field: str) -> Optional[str]:
        """Get first non-null value for a field."""
        col = self._get_col(category, field)
        if not col or col not in group.columns:
            return None

        for val in group[col].dropna():
            if val:
                return str(val)
        return None

    def _first_non_null_raw(self, group: pd.DataFrame, col: str) -> Optional[any]:
        """Get first non-null raw value."""
        if col not in group.columns:
            return None

        for val in group[col].dropna():
            return val
        return None

    def _merge_array_field(self, group: pd.DataFrame, category: str, field: str) -> list[str]:
        """Merge and deduplicate array field."""
        col = self._get_col(category, field)
        if not col or col not in group.columns:
            return []

        merged = []
        for val in group[col].dropna():
            if isinstance(val, list):
                merged.extend(val)

        return self._dedupe_preserve_order(merged)

    def _dedupe_preserve_order(self, items: list[str]) -> list[str]:
        """Deduplicate while preserving order."""
        seen = set()
        result = []
        for item in items:
            if item and item not in seen:
                result.append(item)
                seen.add(item)
        return result

    def _build_skill_vocabulary(self):
        """
        Build skill vocabulary from CSV for fuzzy/embedding matching (Phase 3).

        Extracts all unique skills from:
        - Course Skills Array
        - Course Skills Subject Array
        """
        all_skills = set()

        for course_entity in self.courses.values():
            # Add from Course Skills Array
            for skill in course_entity.course_skills_array:
                if skill:
                    all_skills.add(skill)

            # Add from Course Skills Subject Array
            for skill in course_entity.course_skills_subject_array:
                if skill:
                    all_skills.add(skill)

        self.skill_vocabulary = sorted(list(all_skills))

    def _initialize_embeddings(self):
        """Initialize embeddings manager for semantic search."""
        self.embeddings_manager = EmbeddingsManager(
            openai_api_key=self._openai_api_key
        )

        if self.embeddings_manager.client:
            success = self.embeddings_manager.initialize(
                csv_path=self.csv_path,
                skills=self.skill_vocabulary
            )
            if success:
                logger.info(f"Embeddings initialized with {len(self.skill_vocabulary)} skills")
            else:
                logger.warning("Failed to initialize embeddings - falling back to keyword search")
        else:
            logger.info("Embeddings disabled - using keyword search only")

    def _extract_intent(self, query: str) -> dict:
        """
        Extract intent from transition/upskilling queries.

        Detects patterns like:
        - "from X to Y" / "from X into Y"
        - "become a Y" / "become Y"
        - "transition to Y" / "move to Y"
        - "upskill to Y" / "train as Y"
        - "to be Y" / "to be a Y"

        Returns:
            dict with 'target_terms' (boosted), 'source_terms' (deprioritized),
            'target_role' (detected job title), 'target_skills' (expanded skills)
        """
        import re
        query_lower = query.lower()

        target_terms = []
        source_terms = []
        target_role = None
        source_role = None

        # First, try to detect job titles in the query
        for role in self.ROLE_SKILLS_MAP.keys():
            if role in query_lower:
                # Check if it's in a target context
                target_patterns = [
                    rf'become\s+(?:a\s+)?{re.escape(role)}',
                    rf'to\s+(?:be\s+)?(?:a\s+)?{re.escape(role)}',
                    rf'into\s+(?:a\s+)?{re.escape(role)}',
                    rf'as\s+(?:a\s+)?{re.escape(role)}',
                ]
                for pattern in target_patterns:
                    if re.search(pattern, query_lower):
                        target_role = role
                        break

                # Check if it's in a source context
                source_patterns = [
                    rf'from\s+(?:a\s+)?{re.escape(role)}',
                    rf'upskill\s+(?:\d+\s+)?(?:of\s+)?(?:my\s+|our\s+)?{re.escape(role)}',
                    rf'train\s+(?:\d+\s+)?(?:of\s+)?(?:my\s+|our\s+)?{re.escape(role)}',
                ]
                for pattern in source_patterns:
                    if re.search(pattern, query_lower):
                        source_role = role
                        break

        # Pattern: "from X to/into Y" - X is source, Y is target
        from_to_match = re.search(
            r'from\s+(?:a\s+)?(.+?)\s+(?:to|into)\s+(?:a\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but))',
            query_lower
        )
        if from_to_match:
            source_terms.extend(re.findall(r'\b[a-z]+\b', from_to_match.group(1)))
            target_terms.extend(re.findall(r'\b[a-z]+\b', from_to_match.group(2)))

        # Pattern: "to be (a) Y" - Y is target
        to_be_match = re.search(
            r'to\s+be\s+(?:a\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but))',
            query_lower
        )
        if to_be_match:
            target_terms.extend(re.findall(r'\b[a-z]+\b', to_be_match.group(1)))

        # Pattern: "become (a) Y" - Y is target
        become_match = re.search(
            r'become\s+(?:a\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but))',
            query_lower
        )
        if become_match:
            target_terms.extend(re.findall(r'\b[a-z]+\b', become_match.group(1)))

        # Pattern: "transition/move/switch to Y" - Y is target
        transition_match = re.search(
            r'(?:transition|move|switch)\s+to\s+(?:a\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but))',
            query_lower
        )
        if transition_match:
            target_terms.extend(re.findall(r'\b[a-z]+\b', transition_match.group(1)))

        # Pattern: "upskill/train (them/people) as/to be Y" - Y is target
        upskill_match = re.search(
            r'(?:upskill|train|reskill).*?(?:as|to\s+be)\s+(?:a\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but))',
            query_lower
        )
        if upskill_match:
            target_terms.extend(re.findall(r'\b[a-z]+\b', upskill_match.group(1)))

        # Pattern: "upskill/train X to become/be Y" - X is source (current role), Y is target
        upskill_role_match = re.search(
            r'(?:upskill|train|reskill)\s+(?:\d+\s+)?(?:of\s+)?(?:my\s+|our\s+)?(.+?)\s+to\s+(?:become\s+)?(?:be\s+)?(?:a\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but|what))',
            query_lower
        )
        if upskill_role_match:
            source_terms.extend(re.findall(r'\b[a-z]+\b', upskill_role_match.group(1)))
            target_terms.extend(re.findall(r'\b[a-z]+\b', upskill_role_match.group(2)))

        # Pattern: "learn Y" / "learning Y" - Y is target
        learn_match = re.search(
            r'(?:learn|learning)\s+(?:about\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but))',
            query_lower
        )
        if learn_match:
            target_terms.extend(re.findall(r'\b[a-z]+\b', learn_match.group(1)))

        # Pattern: "already know/have X" - X is existing skill (source)
        already_match = re.search(
            r'already\s+(?:know|have|has|knowing|having|experienced|familiar)\s+(?:with\s+)?(.+?)(?:\.|,|$|\s+(?:they|who|that|and|but|what))',
            query_lower
        )
        if already_match:
            source_terms.extend(re.findall(r'\b[a-z]+\b', already_match.group(1)))

        # Pattern: "know/knows X" - X is existing skill (source)
        know_match = re.search(
            r'(?:they|who|people)\s+(?:already\s+)?know(?:s)?\s+(.+?)(?:\.|,|$|\s+(?:and|but|what))',
            query_lower
        )
        if know_match:
            source_terms.extend(re.findall(r'\b[a-z]+\b', know_match.group(1)))

        # Filter out stop words from extracted terms
        stop_words = {'a', 'an', 'the', 'be', 'is', 'are', 'as', 'to', 'for', 'and', 'or', 'become', 'what', 'do', 'you', 'recommend'}
        target_terms = [t for t in target_terms if t not in stop_words and len(t) > 1]
        source_terms = [t for t in source_terms if t not in stop_words and len(t) > 1]

        # Remove duplicates while preserving order
        seen = set()
        target_terms = [t for t in target_terms if not (t in seen or seen.add(t))]
        seen = set()
        source_terms = [t for t in source_terms if not (t in seen or seen.add(t))]

        # Expand target role to skills
        target_skills = []
        if target_role and target_role in self.ROLE_SKILLS_MAP:
            target_skills = self.ROLE_SKILLS_MAP[target_role]
            logger.info(f"Detected target role '{target_role}' -> expanded to skills: {target_skills}")

        # Get source skills (for context, not for searching)
        source_skills = []
        if source_role and source_role in self.ROLE_SKILLS_MAP:
            source_skills = self.ROLE_SKILLS_MAP[source_role]

        return {
            'target_terms': target_terms,
            'source_terms': source_terms,
            'target_role': target_role,
            'source_role': source_role,
            'target_skills': target_skills,
            'source_skills': source_skills,
        }

    def search_programs(
        self,
        query: str,
        top_k: int = 5
    ) -> list[ProgramSearchResult]:
        """
        Search programs with skill-aware ranking + semantic resolution (Phase 3).

        Two-tier evidence strategy:
        1) Coverage: Course Skills Array + Course Skills Subject Array (primary)
        2) Fit: Title/summary fields (secondary)

        Phase 3 enhancement: Uses SkillSemanticResolver to:
        - Map aliases to canonical skills
        - Detect skill intents via taxonomy
        - Add fuzzy/embedding fallback

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of program search results
        """
        query_lower = query.lower()
        # Remove punctuation and split into terms
        import re
        query_terms = re.findall(r'\b[a-z]+\b', query_lower)

        # Extract intent (target vs source skills for transition queries)
        intent = self._extract_intent(query)
        target_terms = set(intent['target_terms'])
        source_terms = set(intent['source_terms'])
        target_role = intent.get('target_role')
        target_skills = intent.get('target_skills', [])

        # If we detected a target role, use the expanded skills as primary search terms
        role_based_search = False
        if target_role and target_skills:
            logger.info(f"Role-based search: '{target_role}' -> searching for skills: {target_skills}")
            role_based_search = True
            # Replace query terms with target skills for role-based queries
            query_terms = target_skills.copy()

        # Filter out common stop words that cause false matches
        stop_words = {
            'i', 'we', 'you', 'they', 'he', 'she', 'it', 'the', 'a', 'an',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may', 'might',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'and', 'or', 'but', 'if', 'then', 'so', 'than', 'that', 'this', 'these', 'those',
            'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'some', 'any', 'no',
            'my', 'your', 'our', 'their', 'its', 'his', 'her',
            'want', 'need', 'know', 'already', 'about', 'get', 'make', 'take',
            'just', 'only', 'also', 'very', 'really', 'well', 'much', 'many',
            'program', 'programs', 'course', 'courses', 'training', 'learn', 'learning',
        }
        query_terms = [t for t in query_terms if t not in stop_words and len(t) > 1]

        # If we have target terms from intent detection, prioritize them
        # and optionally exclude source terms from matching
        if target_terms:
            # Remove source terms from query to avoid matching what user already has
            query_terms = [t for t in query_terms if t not in source_terms]

        # Phase 3: Semantic resolution (skip if we have target intent to avoid adding source-related terms)
        semantic_result = None
        if self.semantic_resolver and not target_terms:
            semantic_result = self.semantic_resolver.resolve(query)
            # Add normalized skills and expansions to search terms
            if semantic_result.normalized_skills:
                query_terms.extend([s.lower() for s in semantic_result.normalized_skills])
            if semantic_result.query_expansions:
                query_terms.extend([s.lower() for s in semantic_result.query_expansions])
            # Remove duplicates while preserving order
            seen = set()
            unique_terms = []
            for term in query_terms:
                if term not in seen:
                    unique_terms.append(term)
                    seen.add(term)
            query_terms = unique_terms

        # Phase 4: Embedding-based semantic search
        # Find semantically similar skills using embeddings
        similar_skills = []
        if self.embeddings_manager and self.embeddings_manager.is_available():
            # Use the original query for semantic search
            similar = self.embeddings_manager.find_similar_skills(
                query=query,
                top_k=15,
                threshold=0.35
            )
            similar_skills = [skill for skill, score in similar]
            if similar_skills:
                logger.debug(f"Semantic search found {len(similar_skills)} similar skills")

        results = []

        for prog_key, prog_entity in self.programs.items():
            score = 0.0
            matched_skills = []
            matched_subjects = []
            matched_courses = []
            source_columns = []
            matched_terms = set()  # Track which query terms matched
            semantic_matches = []  # Track semantically matched skills

            # TIER 0: Semantic skill matches (EMBEDDING-BASED)
            if similar_skills:
                for similar_skill in similar_skills:
                    similar_lower = similar_skill.lower()
                    for prog_skill in prog_entity.skills_union:
                        if similar_lower == prog_skill.lower():
                            score += 15.0  # Strong boost for semantic matches
                            if prog_skill not in semantic_matches:
                                semantic_matches.append(prog_skill)
                            if 'Semantic Match' not in source_columns:
                                source_columns.append('Semantic Match')
                            break

            # TIER 1: Exact/partial skill matches (PRIMARY EVIDENCE)
            for term in query_terms:
                # Check course skills array - use word boundary matching
                term_pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                for skill in prog_entity.skills_union:
                    if term_pattern.search(skill):
                        # Determine weight based on intent
                        if term in target_terms:
                            weight = 25.0  # Boost target terms significantly
                        elif term in source_terms:
                            weight = 2.0   # Deprioritize source terms
                        else:
                            weight = 10.0  # Normal weight
                        score += weight
                        matched_terms.add(term)
                        if skill not in matched_skills:
                            matched_skills.append(skill)
                        if 'Course Skills Array' not in source_columns:
                            source_columns.append('Course Skills Array')

            # Find which courses matched
            for course_key, course_skills in prog_entity.skills_by_course.items():
                for skill in course_skills:
                    if any(re.search(r'\b' + re.escape(term) + r'\b', skill, re.IGNORECASE) for term in query_terms):
                        entity_key = f"{prog_key}:{course_key}"
                        if entity_key in self.courses:
                            course_entity = self.courses[entity_key]
                            matched_courses.append({
                                "course_key": course_key,
                                "course_title": course_entity.course_title
                            })
                        break

            # TIER 2: Contextual matches (SECONDARY EVIDENCE)
            # Course title/summary
            for course_key in prog_entity.courses:
                entity_key = f"{prog_key}:{course_key}"
                if entity_key in self.courses:
                    course_entity = self.courses[entity_key]
                    searchable = f"{course_entity.course_title} {course_entity.course_summary or ''}"
                    for term in query_terms:
                        if re.search(r'\b' + re.escape(term) + r'\b', searchable, re.IGNORECASE):
                            # Determine weight based on intent
                            if term in target_terms:
                                weight = 8.0  # Boost target terms
                            elif term in source_terms:
                                weight = 1.0  # Deprioritize source terms
                            else:
                                weight = 3.0  # Normal weight
                            score += weight
                            matched_terms.add(term)
                            if 'Course Title' not in source_columns:
                                source_columns.append('Course Title')

            # Program title/summary
            searchable_prog = f"{prog_entity.program_title} {prog_entity.program_summary or ''}"
            for term in query_terms:
                if re.search(r'\b' + re.escape(term) + r'\b', searchable_prog, re.IGNORECASE):
                    # Determine weight based on intent
                    if term in target_terms:
                        weight = 6.0  # Boost target terms
                    elif term in source_terms:
                        weight = 0.5  # Deprioritize source terms
                    else:
                        weight = 2.0  # Normal weight
                    score += weight
                    matched_terms.add(term)
                    if 'Program Title' not in source_columns:
                        source_columns.append('Program Title')

            # Lesson/project titles (lower weight, explanatory)
            for course_key in prog_entity.courses:
                entity_key = f"{prog_key}:{course_key}"
                if entity_key in self.courses:
                    course_entity = self.courses[entity_key]
                    for lesson in course_entity.lesson_outline:
                        if any(re.search(r'\b' + re.escape(term) + r'\b', lesson, re.IGNORECASE) for term in query_terms):
                            score += 0.5
                    for project in course_entity.project_titles:
                        if any(re.search(r'\b' + re.escape(term) + r'\b', project, re.IGNORECASE) for term in query_terms):
                            score += 0.5

            if score > 0:
                # Calculate relevance based on:
                # 1. Percentage of query terms matched (primary factor)
                # 2. Raw score (secondary factor for tie-breaking)
                # 3. Semantic matches bonus
                term_coverage = len(matched_terms) / len(query_terms) if query_terms else 0
                semantic_bonus = min(len(semantic_matches) * 0.1, 0.3) if semantic_matches else 0
                # Combine: 60% term coverage + 30% normalized score + 10% semantic
                normalized_score = min(score / (len(query_terms) * 10.0 + len(semantic_matches) * 5.0), 1.0)
                relevance = (0.6 * term_coverage) + (0.3 * normalized_score) + semantic_bonus

                # Combine matched skills with semantic matches
                all_matched_skills = matched_skills + [s for s in semantic_matches if s not in matched_skills]

                results.append(ProgramSearchResult(
                    program_entity=prog_entity,
                    relevance_score=relevance,
                    matched_course_skills=all_matched_skills,
                    matched_course_skill_subjects=matched_subjects,
                    matched_courses=matched_courses,
                    source_columns=source_columns,
                ))

        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]

    def get_program_details(self, program_key: str) -> Optional[ProgramEntity]:
        """Get program-level summary."""
        return self.programs.get(program_key)

    def get_program_deep_details(self, program_key: str) -> Optional[dict]:
        """
        Get deep program details with courses.

        Returns:
            Dict with program entity and course entities
        """
        if program_key not in self.programs:
            return None

        prog_entity = self.programs[program_key]

        # Get all courses
        course_entities = []
        for course_key in prog_entity.courses:
            entity_key = f"{program_key}:{course_key}"
            if entity_key in self.courses:
                course_entities.append(self.courses[entity_key])

        return {
            "program": prog_entity,
            "courses": course_entities,
        }

    def get_details(self, program_keys: list[str]) -> list[CSVDetail]:
        """
        Get details for compatibility with existing CSVDetailsAgent.

        This converts our new aggregated format back to the CSVDetail format
        used by existing agents.

        Args:
            program_keys: List of program keys

        Returns:
            List of CSVDetail objects
        """
        results = []

        for prog_key in program_keys:
            if prog_key not in self.programs:
                continue

            prog_entity = self.programs[prog_key]

            # Get first course for backward compatibility
            if not prog_entity.courses:
                continue

            first_course_key = prog_entity.courses[0]
            entity_key = f"{prog_key}:{first_course_key}"

            if entity_key not in self.courses:
                continue

            course_entity = self.courses[entity_key]

            # Convert to CSVDetail format
            detail = CSVDetail(
                program_key=prog_key,
                program_title=prog_entity.program_title,
                course_title=course_entity.course_title,
                prerequisite_skills=course_entity.course_prereq_skills,
                course_skills=course_entity.course_skills_array + course_entity.course_skills_subject_array,
                third_party_tools=course_entity.third_party_tools,
                software_requirements=course_entity.software_requirements,
                hardware_requirements=course_entity.hardware_requirements,
                lesson_titles=course_entity.lesson_outline,
                lesson_summaries=[],  # Not available in aggregated format
                project_titles=course_entity.project_titles,
                concept_titles=course_entity.concept_titles,
                duration_hours=prog_entity.program_duration_hours,
                difficulty_level=prog_entity.difficulty_level,
            )

            results.append(detail)

        return results
