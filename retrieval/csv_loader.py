"""CSV loader with parsing and cleaning logic."""

import pandas as pd
import yaml
from pathlib import Path
from typing import Optional, Any


class CSVLoader:
    """Load and clean CSV data with proper normalization."""

    def __init__(self, columns_config_path: Optional[str] = None):
        """
        Initialize CSV loader.

        Args:
            columns_config_path: Path to columns.yaml config
        """
        if columns_config_path is None:
            # Default to config/columns.yaml
            base_path = Path(__file__).parent.parent
            columns_config_path = base_path / "config" / "columns.yaml"

        with open(columns_config_path, 'r') as f:
            self.column_mapping = yaml.safe_load(f)

    def load_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Load CSV file with proper cleaning.

        Args:
            csv_path: Path to CSV file

        Returns:
            Cleaned DataFrame
        """
        # Try different encodings and delimiters
        encodings = ['utf-16', 'utf-8', 'latin-1']
        delimiters = ['\t', ',']
        df = None

        for encoding in encodings:
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding, delimiter=delimiter)
                    break
                except (UnicodeDecodeError, UnicodeError, pd.errors.ParserError):
                    continue
            if df is not None:
                break

        if df is None:
            raise ValueError(f"Could not read CSV with any supported encoding/delimiter: {encodings}/{delimiters}")

        # Clean the DataFrame
        df = self._clean_dataframe(df)

        return df

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame with normalization rules.

        Args:
            df: Raw DataFrame

        Returns:
            Cleaned DataFrame
        """
        # Make a copy to avoid modifying original
        df = df.copy()

        # Normalize nulls
        df = self._normalize_nulls(df)

        # Clean boolean fields
        boolean_fields = self._get_column_names(['in_consumer_catalog', 'in_ent_catalog'])
        for field in boolean_fields:
            if field in df.columns:
                df[field] = self._parse_boolean(df[field])

        # Clean numeric fields
        numeric_fields = self._get_column_names([
            'program_duration_hours',
            'course_duration_hours',
            'lesson_duration_hours',
            'total_active_enrollments'
        ])
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        # Clean array fields
        array_fields = self._get_column_names([
            'course_skills_array',
            'course_skills_subject_array',
            'skill_domains',
            'concept_titles',
            'prerequisite_skills',
            'course_prereq_skills',
            'third_party_tools',
            'software_requirements',
            'hardware_requirements',
            'gtm_array',
            'partners',
            'clients'
        ])
        for field in array_fields:
            if field in df.columns:
                df[field] = df[field].apply(self._parse_array)

        return df

    def _normalize_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize null values."""
        # Replace various null representations with None
        null_values = ["Null", "null", "NULL", "", "nan", "NaN", "NAN"]
        df = df.replace(null_values, None)
        return df

    def _parse_boolean(self, series: pd.Series) -> pd.Series:
        """Parse boolean values."""
        def to_bool(val):
            if pd.isna(val) or val is None:
                return False
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                val_lower = val.lower().strip()
                if val_lower in ['true', 't', 'yes', 'y', '1']:
                    return True
                if val_lower in ['false', 'f', 'no', 'n', '0']:
                    return False
            return False

        return series.apply(to_bool)

    def _parse_array(self, value: Any) -> list[str]:
        """
        Parse array field.

        Rules:
        - Split by comma
        - Strip whitespace
        - Drop empty or "null"
        - Deduplicate while preserving order

        Args:
            value: Raw value

        Returns:
            Parsed list
        """
        if pd.isna(value) or value is None:
            return []

        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            items = value.split(',')
        else:
            return []

        # Clean items
        cleaned = []
        seen = set()
        for item in items:
            item = str(item).strip()
            # Skip empty or null values
            if not item or item.lower() in ['null', 'nan', '']:
                continue
            # Deduplicate while preserving order
            if item not in seen:
                cleaned.append(item)
                seen.add(item)

        return cleaned

    def _get_column_names(self, logical_names: list[str]) -> list[str]:
        """
        Get actual column names from logical names.

        Args:
            logical_names: List of logical field names

        Returns:
            List of actual column names
        """
        column_names = []
        for logical_name in logical_names:
            # Search in program, course, and lesson mappings
            for category in ['program', 'course', 'lesson']:
                if category in self.column_mapping:
                    if logical_name in self.column_mapping[category]:
                        actual_names = self.column_mapping[category][logical_name]
                        if isinstance(actual_names, list):
                            column_names.extend(actual_names)
                        else:
                            column_names.append(actual_names)

        return column_names

    def get_column_name(self, category: str, logical_name: str) -> Optional[str]:
        """
        Get actual column name for a logical field.

        Args:
            category: 'program', 'course', or 'lesson'
            logical_name: Logical field name

        Returns:
            Actual column name or None
        """
        if category not in self.column_mapping:
            return None

        if logical_name not in self.column_mapping[category]:
            return None

        actual_names = self.column_mapping[category][logical_name]
        if isinstance(actual_names, list) and len(actual_names) > 0:
            return actual_names[0]

        return actual_names
