"""Azure AI Search index schema with optimized field settings."""

from typing import Dict, Any


def create_index_schema(index_name: str) -> Dict[str, Any]:
    """
    Create optimized index schema for Udacity programs.

    Field optimization strategy (to minimize storage):
    - searchable: Only program_title (for keyword fallback)
    - filterable: Only program_key, difficulty_level, program_type
    - sortable: Only duration_hours
    - retrievable: All fields we need to return
    - Vector field: skills_vector (1536 dimensions)

    Args:
        index_name: Name of the index

    Returns:
        Index schema dictionary
    """
    return {
        "name": index_name,
        "fields": [
            # Primary key - filterable for lookups
            {
                "name": "id",
                "type": "Edm.String",
                "key": True,
                "searchable": False,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            # Program identifiers
            {
                "name": "program_key",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,  # Need for lookups
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "course_key",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            # Title - only searchable text field
            {
                "name": "program_title",
                "type": "Edm.String",
                "searchable": True,  # Only searchable text field
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True,
                "analyzer": "standard.lucene"
            },
            {
                "name": "course_title",
                "type": "Edm.String",
                "searchable": False,  # Not searchable to save space
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            # Summaries - retrievable only (large text)
            {
                "name": "course_summary",
                "type": "Edm.String",
                "searchable": False,  # Large text - don't index
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            # Skills - retrievable only (used for embedding)
            {
                "name": "skills",
                "type": "Edm.String",
                "searchable": False,  # Already embedded
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "skill_subjects",
                "type": "Edm.String",
                "searchable": False,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "skill_domains",
                "type": "Edm.String",
                "searchable": False,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            # Metadata - minimal indexing
            {
                "name": "program_type",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,  # Useful for filtering
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "difficulty_level",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,  # Useful for filtering
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "duration_hours",
                "type": "Edm.Double",
                "searchable": False,
                "filterable": True,
                "sortable": True,  # Only sortable numeric field
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "prerequisites",
                "type": "Edm.String",
                "searchable": False,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "software_requirements",
                "type": "Edm.String",
                "searchable": False,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            {
                "name": "projects",
                "type": "Edm.String",
                "searchable": False,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True
            },
            # Vector field for semantic search
            {
                "name": "skills_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,  # Don't return vectors
                "dimensions": 1536,
                "vectorSearchProfile": "vector-profile"
            }
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "hnsw-algorithm",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500
                    }
                }
            ],
            "profiles": [
                {
                    "name": "vector-profile",
                    "algorithm": "hnsw-algorithm"
                }
            ]
        }
    }
