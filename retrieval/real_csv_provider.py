"""Real CSV provider with skill-based search and aggregation."""

import pandas as pd
from typing import Optional
from collections import defaultdict
from retrieval.csv_loader import CSVLoader
from schemas.aggregated import ProgramEntity, CourseEntity, ProgramSearchResult
from schemas.evidence import CSVDetail


class RealCSVProvider:
    """Real CSV provider for Phase 2."""

    def __init__(self, csv_path: str):
        """
        Initialize with real CSV file.

        Args:
            csv_path: Path to CSV file
        """
        self.csv_path = csv_path
        self.loader = CSVLoader()
        self.df: Optional[pd.DataFrame] = None
        self.programs: dict[str, ProgramEntity] = {}
        self.courses: dict[str, CourseEntity] = {}

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
            skills_by_course = {}

            for course_key in prog_entity.courses:
                entity_key = f"{prog_key}:{course_key}"
                if entity_key in self.courses:
                    course_entity = self.courses[entity_key]
                    course_skills = course_entity.course_skills_array + course_entity.course_skills_subject_array
                    skills_union.update(course_skills)
                    if course_skills:
                        skills_by_course[course_key] = course_skills

            prog_entity.skills_union = list(skills_union)
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

    def search_programs(
        self,
        query: str,
        top_k: int = 5
    ) -> list[ProgramSearchResult]:
        """
        Search programs with skill-aware ranking.

        Two-tier evidence strategy:
        1) Coverage: Course Skills Array + Course Skills Subject Array (primary)
        2) Fit: Title/summary fields (secondary)

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of program search results
        """
        query_lower = query.lower()
        query_terms = query_lower.split()

        results = []

        for prog_key, prog_entity in self.programs.items():
            score = 0.0
            matched_skills = []
            matched_subjects = []
            matched_courses = []
            source_columns = []

            # TIER 1: Exact/partial skill matches (PRIMARY EVIDENCE)
            for term in query_terms:
                # Check course skills array
                for skill in prog_entity.skills_union:
                    if term in skill.lower():
                        score += 10.0  # Highest weight
                        if skill not in matched_skills:
                            matched_skills.append(skill)
                        if 'Course Skills Array' not in source_columns:
                            source_columns.append('Course Skills Array')

            # Find which courses matched
            for course_key, course_skills in prog_entity.skills_by_course.items():
                for skill in course_skills:
                    if any(term in skill.lower() for term in query_terms):
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
                    searchable = f"{course_entity.course_title} {course_entity.course_summary or ''}".lower()
                    for term in query_terms:
                        if term in searchable:
                            score += 3.0  # Medium weight
                            if 'Course Title' not in source_columns:
                                source_columns.append('Course Title')

            # Program title/summary
            searchable_prog = f"{prog_entity.program_title} {prog_entity.program_summary or ''}".lower()
            for term in query_terms:
                if term in searchable_prog:
                    score += 2.0  # Medium weight
                    if 'Program Title' not in source_columns:
                        source_columns.append('Program Title')

            # Lesson/project titles (lower weight, explanatory)
            for course_key in prog_entity.courses:
                entity_key = f"{prog_key}:{course_key}"
                if entity_key in self.courses:
                    course_entity = self.courses[entity_key]
                    for lesson in course_entity.lesson_outline:
                        if any(term in lesson.lower() for term in query_terms):
                            score += 0.5
                    for project in course_entity.project_titles:
                        if any(term in project.lower() for term in query_terms):
                            score += 0.5

            if score > 0:
                # Normalize score
                relevance = min(score / (len(query_terms) * 10.0), 1.0)

                results.append(ProgramSearchResult(
                    program_entity=prog_entity,
                    relevance_score=relevance,
                    matched_course_skills=matched_skills,
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
