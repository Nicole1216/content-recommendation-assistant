"""CSV index for detailed program information."""

import pandas as pd
from typing import Optional
from schemas.evidence import CSVDetail


class CSVIndex:
    """Index for CSV data with mock implementation."""

    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize CSV index.

        Args:
            csv_path: Path to CSV file (optional in Phase 1)
        """
        self.csv_path = csv_path
        self._df: Optional[pd.DataFrame] = None
        self._mock_data = self._create_mock_data()

    def _create_mock_data(self) -> list[CSVDetail]:
        """Create mock CSV detail data."""
        return [
            CSVDetail(
                program_key="cd0000",
                program_title="AI Programming with Python",
                course_title="Introduction to Python",
                prerequisite_skills=["Basic computer literacy", "High school math"],
                course_skills=["Python", "NumPy", "Pandas", "Neural Networks"],
                third_party_tools=["Jupyter Notebook", "VS Code"],
                software_requirements=["Python 3.8+", "Anaconda"],
                hardware_requirements=["4GB RAM minimum", "Webcam for proctoring"],
                lesson_titles=[
                    "Python Basics",
                    "Data Structures",
                    "NumPy Fundamentals",
                    "Neural Network Math",
                    "Building Your First NN"
                ],
                lesson_summaries=[
                    "Variables, loops, functions",
                    "Lists, dicts, sets",
                    "Array operations",
                    "Linear algebra review",
                    "Implement backpropagation"
                ],
                project_titles=["Image Classifier", "Dog Breed Classifier"],
                concept_titles=["Variables", "Functions", "Classes", "Gradient Descent"],
                duration_hours=120.0,
                difficulty_level="Beginner",
            ),
            CSVDetail(
                program_key="cd0101",
                program_title="Generative AI for Business Leaders",
                course_title="GenAI Business Applications",
                prerequisite_skills=[],
                course_skills=["GenAI Strategy", "Use Case Identification", "ROI Analysis"],
                third_party_tools=[],
                software_requirements=[],
                hardware_requirements=[],
                lesson_titles=[
                    "What is GenAI?",
                    "Business Use Cases",
                    "Implementation Roadmap",
                    "Risk & Ethics"
                ],
                lesson_summaries=[
                    "LLMs, diffusion models, key concepts",
                    "Customer service, content, code generation",
                    "Pilot to production",
                    "Bias, security, compliance"
                ],
                project_titles=[],
                concept_titles=["LLMs", "Prompts", "Fine-tuning", "RAG"],
                duration_hours=8.0,
                difficulty_level="Beginner",
            ),
            CSVDetail(
                program_key="cd0102",
                program_title="Data Analyst Nanodegree",
                course_title="SQL and Data Analysis",
                prerequisite_skills=["Basic Excel", "Basic statistics"],
                course_skills=["SQL", "Python", "Pandas", "Tableau", "Statistics"],
                third_party_tools=["PostgreSQL", "Tableau", "Jupyter"],
                software_requirements=["PostgreSQL 12+", "Python 3.8+", "Tableau Desktop"],
                hardware_requirements=["8GB RAM recommended"],
                lesson_titles=[
                    "SQL Fundamentals",
                    "Advanced SQL",
                    "Python for Data Analysis",
                    "Data Visualization",
                    "Statistics Fundamentals"
                ],
                lesson_summaries=[
                    "SELECT, JOIN, GROUP BY",
                    "Window functions, CTEs, optimization",
                    "Pandas, NumPy for data wrangling",
                    "Tableau dashboards, storytelling",
                    "Descriptive stats, hypothesis testing"
                ],
                project_titles=[
                    "Sales Dashboard",
                    "A/B Test Analysis",
                    "Customer Segmentation"
                ],
                concept_titles=["Joins", "Aggregations", "DataFrames", "Visualization"],
                duration_hours=180.0,
                difficulty_level="Intermediate",
            ),
            CSVDetail(
                program_key="cd0103",
                program_title="GenAI Prompt Engineering",
                course_title="Prompt Engineering Masterclass",
                prerequisite_skills=["Basic understanding of AI"],
                course_skills=["Prompt Engineering", "Chain-of-Thought", "RAG"],
                third_party_tools=["OpenAI API", "Anthropic Claude", "LangChain"],
                software_requirements=["API access to LLM providers"],
                hardware_requirements=[],
                lesson_titles=[
                    "Prompt Basics",
                    "Advanced Techniques",
                    "Prompt Chaining",
                    "RAG Systems"
                ],
                lesson_summaries=[
                    "Zero-shot, few-shot, role prompting",
                    "Chain-of-thought, self-consistency",
                    "Multi-step reasoning",
                    "Retrieval-augmented generation"
                ],
                project_titles=["Build a RAG Chatbot", "Prompt Library"],
                concept_titles=["Few-shot", "CoT", "RAG", "Temperature"],
                duration_hours=12.0,
                difficulty_level="Beginner",
            ),
            CSVDetail(
                program_key="cd0104",
                program_title="Machine Learning Engineer Nanodegree",
                course_title="Production ML Systems",
                prerequisite_skills=["Python", "Statistics", "Linear Algebra"],
                course_skills=["ML Engineering", "MLOps", "Model Deployment", "AWS SageMaker"],
                third_party_tools=["AWS SageMaker", "Docker", "Kubernetes", "MLflow"],
                software_requirements=["AWS account", "Docker", "Python 3.8+"],
                hardware_requirements=["GPU recommended for training"],
                lesson_titles=[
                    "ML Review",
                    "Model Training at Scale",
                    "Deployment Pipelines",
                    "Monitoring & Retraining"
                ],
                lesson_summaries=[
                    "Supervised learning refresher",
                    "Distributed training, hyperparameter tuning",
                    "CI/CD for ML, SageMaker endpoints",
                    "Drift detection, A/B testing"
                ],
                project_titles=[
                    "Deploy Sentiment Model",
                    "Build ML Pipeline",
                    "Capstone: End-to-end System"
                ],
                concept_titles=["Pipelines", "Endpoints", "Monitoring", "Retraining"],
                duration_hours=240.0,
                difficulty_level="Advanced",
            ),
            CSVDetail(
                program_key="cd0105",
                program_title="GenAI for Product Managers",
                course_title="GenAI Product Strategy",
                prerequisite_skills=["Product management basics"],
                course_skills=["GenAI Strategy", "Product Roadmapping", "Vendor Evaluation"],
                third_party_tools=[],
                software_requirements=[],
                hardware_requirements=[],
                lesson_titles=[
                    "GenAI Product Landscape",
                    "Use Case Prioritization",
                    "Build vs Buy",
                    "Measuring Success"
                ],
                lesson_summaries=[
                    "Market trends, capabilities",
                    "Impact/effort matrix for AI features",
                    "Vendor selection, API integration",
                    "KPIs, user adoption, ROI"
                ],
                project_titles=["GenAI Product Brief", "Vendor Scorecard"],
                concept_titles=["Product-Market Fit", "ROI", "Adoption Metrics"],
                duration_hours=10.0,
                difficulty_level="Beginner",
            ),
        ]

    def load(self):
        """Load CSV file (mocked in Phase 1)."""
        if self.csv_path:
            # In Phase 2, load actual CSV:
            # self._df = pd.read_csv(self.csv_path)
            pass

    def get_details(self, program_keys: list[str]) -> list[CSVDetail]:
        """
        Get detailed information for specific programs.

        Args:
            program_keys: List of program keys

        Returns:
            List of CSV details
        """
        results = []
        for key in program_keys:
            for detail in self._mock_data:
                if detail.program_key == key:
                    results.append(detail)
                    break
        return results

    def search_by_skill(self, skill: str, top_k: int = 5) -> list[CSVDetail]:
        """
        Search programs by skill.

        Args:
            skill: Skill to search for
            top_k: Number of results

        Returns:
            List of matching programs
        """
        skill_lower = skill.lower()
        results = []

        for detail in self._mock_data:
            # Check if skill appears in course_skills
            for course_skill in detail.course_skills:
                if skill_lower in course_skill.lower():
                    results.append(detail)
                    break

        return results[:top_k]

    def search_by_tools(self, tool: str) -> list[CSVDetail]:
        """Search programs by tool."""
        tool_lower = tool.lower()
        results = []

        for detail in self._mock_data:
            for t in detail.third_party_tools:
                if tool_lower in t.lower():
                    results.append(detail)
                    break

        return results
