from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
import json
import requests
import os
from dotenv import load_dotenv

from app.models import Document, Project
from app.schemas import ProjectRequest, ProjectAnalysis, AnalysisResponse, ProjectRequestWithTech, TechStackResponse
from app.service.document_service import DocumentService

load_dotenv()

class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_service = DocumentService(db)
    
    # async def analyze_project(self, document: Document, project_request: ProjectRequest, user_id: int) -> AnalysisResponse:
    #     """Analyze project document and create project record"""
    #     try:
    #         analysis_content = self._prepare_analysis_content(document)
            
    #         analysis_prompt = f"""
    #         Please analyze this project document and provide:
    #         1. Project name (generate if not provided: {project_request.project_name})
    #         2. Project summary and scope
    #         3. Time estimation with human buffer (daily hours: {project_request.daily_hours}, working days: {project_request.working_days_per_week})
    #         4. Developer tasks breakdown
    #         5. Technology recommendations
    #         6. Project complexity assessment
            
    #         Include 1.5x buffer multiplier for realistic human work estimation.
    #         """
            
    #         mistral_response = self._call_mistral_api(
    #             analysis_prompt, 
    #             analysis_content, 
    #             project_request.project_name, 
    #             project_request.daily_hours, 
    #             project_request.working_days_per_week
    #         )
            
    #         analysis = self._parse_mistral_response(mistral_response)
            
    #         project_id = await self._create_project_record(
    #             analysis, document, user_id
    #         )
            
    #         return AnalysisResponse(
    #             success=True,
    #             message="Project analysis completed successfully",
    #             analysis=analysis,
    #             project_id=project_id
    #         )
            
    #     except Exception as e:
    #         return AnalysisResponse(
    #             success=False,
    #             message="Analysis failed",
    #             error=str(e)
    #         )

    async def analyze_project(self, document: Document, project_request: ProjectRequest, user_id: int) -> AnalysisResponse:
        """Analyze project document and create project record"""
        try:
            analysis_content = self._prepare_analysis_content(document)
            
            analysis_prompt = f"""
    Please analyze this project document and provide:
    1. Project name (generate if not provided: {project_request.project_name})
    2. Project summary and scope
    3. Time estimation with human buffer (daily hours: {project_request.daily_hours}, working days: {project_request.working_days_per_week})
    4. Developer tasks breakdown
    5. Technology recommendations or use user-specified technologies: {project_request.technologies}
    6. Project complexity assessment

    Include 1.5x buffer multiplier for realistic human work estimation.
    """
            
            mistral_response = self._call_mistral_api(
                prompt=analysis_prompt,
                document_context=analysis_content,
                project_name=project_request.project_name,
                daily_hours=project_request.daily_hours,
                working_days_per_week=project_request.working_days_per_week,
                technologies=project_request.technologies  # pass technologies to API call
            )
            
            analysis = self._parse_mistral_response(mistral_response)
            
            project_id = await self._create_project_record(
                analysis, document, user_id
            )
            
            return AnalysisResponse(
                success=True,
                message="Project analysis completed successfully",
                analysis=analysis,
                project_id=project_id
            )
            
        except Exception as e:
            return AnalysisResponse(
                success=False,
                message="Analysis failed",
                error=str(e)
            )

    
    def _prepare_analysis_content(self, document: Document) -> str:
        """Prepare document content for analysis"""
        content = document.content
        if len(content) > 8000:
            content = content[:8000] + "..."
        return content
    
#     def _call_mistral_api(self, prompt: str, document_context: str, project_name: str = None, daily_hours: int = 8, working_days_per_week: int = 5) -> str:
#         """Call Mistral API for project analysis"""
#         buffer_multiplier = 1.5
#         system_prompt = f"""You are an expert Project Analysis Assistant specialized in software development project estimation and planning.

# CORE CAPABILITIES:
# 1. Project Requirements Analysis
# 2. Scope & Deliverables Identification  
# 3. Realistic Time & Resource Planning with Human Buffer
# 4. Work Estimation & Task Breakdown

# ANALYSIS RULES:
# - FIRST calculate the BASE hours needed for the project (without buffer)
# - THEN apply the {buffer_multiplier}x buffer to get REALISTIC hours
# - FINALLY calculate duration based on REALISTIC hours and working schedule
# - Duration should DECREASE if daily hours increase (same total work spread over fewer days)
# - Total realistic hours should stay CONSTANT regardless of schedule
# - ONLY analyze based on the provided document context
# - If document context is insufficient, state "Insufficient information in document for complete analysis"
# - Provide specific, actionable insights
# - Be realistic in estimations with human buffer included
# - Consider modern development practices

# WORK SCHEDULE PARAMETERS:
# - Daily working hours: {daily_hours} hours
# - Working days per week: {working_days_per_week} days
# - Buffer multiplier: {buffer_multiplier}x (applied after base estimation)

# RESPONSE FORMAT REQUIREMENTS:
# Return a valid JSON object with the following structure:
# {{
#     "project_name": "{{AUTO-GENERATED PROJECT NAME if not provided else use provided name}}",
#     "project_summary": "Brief overview of the project (2-3 sentences)",
#     "scope_and_deliverables": "Detailed scope and key deliverables",
#     "time_estimation": {{
#         "base_hours_required": "X hours (before buffer)",
#         "total_hours_estimated": "X hours (including {buffer_multiplier}x buffer)",
#         "total_duration_weeks": "X weeks (based on {daily_hours}h/day, {working_days_per_week}d/wk)",
#         "total_duration_days": "X working days",
#         "development_phase": "X weeks",
#         "testing_phase": "X weeks", 
#         "deployment_phase": "X days",
#         "buffer_included": "Yes - {buffer_multiplier}x multiplier applied"
#     }},
#     "developer_tasks": [
#         "Task 1: Detailed task description with estimated hours",
#         "Task 2: Another detailed task with estimated hours"
#     ],
#     "technology_stack": ["Technologies mentioned or recommended"],
#     "complexity_level": "Low/Medium/High/Expert"
# }}

# ESTIMATION METHODOLOGY:
# 1. Calculate BASE hours needed (without buffer)
# 2. Apply {buffer_multiplier}x buffer: realistic_hours = base_hours * {buffer_multiplier}
# 3. Calculate duration:
#    - working_hours_per_week = {daily_hours} * {working_days_per_week}
#    - total_weeks = realistic_hours / working_hours_per_week
#    - total_days = realistic_hours / {daily_hours}
# """

#         project_context = f"Project Name: {project_name}" if project_name else "Please generate an appropriate project name based on the document content."

#         user_prompt = f"""
# ANALYSIS REQUEST: {prompt}

# {project_context}

# WORK PARAMETERS:
# - Daily Hours: {daily_hours}
# - Working Days/Week: {working_days_per_week}
# - Buffer Multiplier: {buffer_multiplier}x (for realistic human work estimation)

# DOCUMENT CONTENT:
# {document_context}

# Please analyze this project document and:
# 1. First estimate the BASE hours required (without buffer)
# 2. Then calculate REALISTIC hours by applying {buffer_multiplier}x buffer
# 3. Finally calculate duration based on REALISTIC hours and the work schedule
# 4. Ensure total realistic hours stay constant regardless of schedule
# 5. Show duration decreases when daily hours increase
# """

#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
#         }

#         data = {
#             "model": "mistral-small-latest",
#             "messages": [
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt}
#             ],
#             "temperature": 0.3,
#             "max_tokens": 2000
#         }

#         try:
#             response = requests.post(
#                 "https://api.mistral.ai/v1/chat/completions", 
#                 headers=headers, 
#                 json=data,
#                 timeout=30
#             )
            
#             if response.status_code != 200:
#                 raise Exception(f"Mistral API error: {response.text}")
            
#             result = response.json()
#             return result["choices"][0]["message"]["content"]
            
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"API request failed: {str(e)}")

    def _call_mistral_api(
        self,
        prompt: str,
        document_context: str,
        project_name: str = None,
        daily_hours: int = 8,
        working_days_per_week: int = 5,
        technologies: Optional[List[str]] = None
    ) -> str:
        """Call Mistral API for project analysis, optionally guided by user-specified technologies"""
        buffer_multiplier = 1.5

        # Construct technology context
        if technologies:
            tech_list = ', '.join(technologies)
            technology_context = (
                f"USER-SPECIFIED TECHNOLOGIES:\n"
                f"The user has requested that the following technologies be used in the project:\n"
                f"{tech_list}\n"
                f"Your analysis MUST incorporate and align with these technologies wherever applicable.\n"
                f"Only suggest alternatives if the provided stack is insufficient or inappropriate."
            )
        else:
            technology_context = (
                "NO TECHNOLOGIES PROVIDED:\n"
                "Please analyze the document and recommend a modern and effective technology stack "
                "based on the project requirements and best practices."
            )

        # Build system prompt
        system_prompt = f"""You are an expert Project Analysis Assistant specialized in software development project estimation and planning.

    CORE CAPABILITIES:
    1. Project Requirements Analysis
    2. Scope & Deliverables Identification  
    3. Realistic Time & Resource Planning with Human Buffer
    4. Work Estimation & Task Breakdown
    5. Technology Recommendation (if user hasn't specified one)

    ANALYSIS RULES:
    - FIRST calculate the BASE hours needed for the project (without buffer)
    - THEN apply the {buffer_multiplier}x buffer to get REALISTIC hours
    - FINALLY calculate duration based on REALISTIC hours and working schedule
    - Duration should DECREASE if daily hours increase (same total work spread over fewer days)
    - Total realistic hours should stay CONSTANT regardless of schedule
    - ONLY analyze based on the provided document context and user-specified preferences
    - If document context is insufficient, state "Insufficient information in document for complete analysis"
    - Provide specific, actionable insights
    - Be realistic in estimations with human buffer included
    - Follow modern development practices
    - Respect and prioritize user-specified technologies if any

    WORK SCHEDULE PARAMETERS:
    - Daily working hours: {daily_hours} hours
    - Working days per week: {working_days_per_week} days
    - Buffer multiplier: {buffer_multiplier}x (applied after base estimation)

    RESPONSE FORMAT REQUIREMENTS:
    Return a valid JSON object with the following structure:
    {{
        "project_name": "{{AUTO-GENERATED PROJECT NAME if not provided else use provided name}}",
        "project_summary": "Brief overview of the project (2-3 sentences)",
        "scope_and_deliverables": "Detailed scope and key deliverables",
        "time_estimation": {{
            "base_hours_required": "X hours (before buffer)",
            "total_hours_estimated": "X hours (including {buffer_multiplier}x buffer)",
            "total_duration_weeks": "X weeks (based on {daily_hours}h/day, {working_days_per_week}d/wk)",
            "total_duration_days": "X working days",
            "development_phase": "X weeks",
            "testing_phase": "X weeks", 
            "deployment_phase": "X days",
            "buffer_included": "Yes - {buffer_multiplier}x multiplier applied"
        }},
        "developer_tasks": [
            "Task 1: Detailed task description with estimated hours",
            "Task 2: Another detailed task with estimated hours"
        ],
        "technology_stack": ["Technologies mentioned or recommended"],
        "complexity_level": "Low/Medium/High/Expert"
    }}"""

        project_context = (
            f"Project Name: {project_name}"
            if project_name else
            "Please generate an appropriate project name based on the document content."
        )

        user_prompt = f"""
    ANALYSIS REQUEST: {prompt}

    {project_context}

    {technology_context}

    WORK PARAMETERS:
    - Daily Hours: {daily_hours}
    - Working Days per Week: {working_days_per_week}
    - Buffer Multiplier: {buffer_multiplier}x (for realistic human work estimation)

    DOCUMENT CONTENT:
    {document_context}

    PLEASE FOLLOW THESE STEPS:
    1. Estimate the BASE hours required (no buffer).
    2. Apply a {buffer_multiplier}x buffer to get REALISTIC hours.
    3. Calculate project duration using the working schedule.
    4. Incorporate user-specified technologies if given. Otherwise, recommend best-fit options.
    5. Ensure your output is in the exact JSON format specified.
    """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
        }

        data = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }

        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Mistral API error: {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")


    def _call_mistral_api_for_daily_tasks(self, project_analysis: dict, target_date: str, day_number: int, daily_hours: int = 8) -> str:
        """Call Mistral API for generating daily task breakdown"""
        
        system_prompt = f"""You are an expert Task Planning Assistant specialized in breaking down software development projects into daily actionable tasks.

    CORE CAPABILITIES:
    1. Daily Task Breakdown from Project Analysis
    2. Realistic Daily Hour Allocation
    3. Task Sequencing and Dependencies
    4. Progress-based Task Planning

    DAILY TASK RULES:
    - Generate tasks for exactly {daily_hours} hours per day
    - Tasks should be specific and actionable
    - Consider logical task dependencies and sequence
    - Each task should have realistic hour estimates
    - Total daily hours must equal {daily_hours}
    - Tasks should align with the overall project timeline
    - Consider development best practices and workflow

    RESPONSE FORMAT REQUIREMENTS:
    Return a valid JSON object with the following structure:
    {{
        "day": "Day {day_number}",
        "date": "{target_date}",
        "planned_hours": {daily_hours},
        "tasks": [
            {{"task": "Specific task description", "estimated_hours": X}},
            {{"task": "Another specific task description", "estimated_hours": X}}
        ]
    }}

    TASK PLANNING METHODOLOGY:
    1. Analyze the project phase for Day {day_number}
    2. Break down complex tasks into daily chunks
    3. Ensure task continuity and logical progression
    4. Allocate exactly {daily_hours} hours across all tasks
    5. Make tasks actionable and measurable
    """

        user_prompt = f"""
    DAILY TASK REQUEST for Day {day_number}

    TARGET DATE: {target_date}
    DAILY HOURS: {daily_hours}

    PROJECT ANALYSIS CONTEXT:
    {project_analysis}

    Please generate a daily task breakdown for Day {day_number} that:
    1. Fits within {daily_hours} hours total
    2. Contains specific, actionable tasks
    3. Follows logical development sequence
    4. Aligns with the project timeline and phases
    5. Each task has realistic hour estimates that sum to {daily_hours}
    """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
        }

        data = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions", 
                headers=headers, 
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Mistral API error: {response.text}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

    
    def _parse_mistral_response(self, response_text: str) -> ProjectAnalysis:
        """Parse Mistral API response and convert to ProjectAnalysis model"""
        try:
            response_text = response_text.strip()
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            json_str = response_text[json_start:json_end]
            analysis_data = json.loads(json_str)
            return ProjectAnalysis(**analysis_data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return ProjectAnalysis(
                project_name="Project Analysis Failed",
                project_summary="Analysis could not be completed due to response parsing error.",
                scope_and_deliverables="Unable to determine from document.",
                time_estimation={
                    "total_duration_weeks": "Unable to estimate", 
                    "total_duration_days": "N/A", 
                    "total_hours_estimated": "N/A",
                    "development_phase": "N/A", 
                    "testing_phase": "N/A", 
                    "deployment_phase": "N/A",
                    "buffer_included": "N/A"
                },
                developer_tasks=["Manual analysis required due to parsing error"],
                technology_stack=["To be determined"],
                complexity_level="Unknown"
            )

    async def _create_project_record(self, analysis: ProjectAnalysis, document: Document, user_id: int) -> int:
        """Create project record in database"""
        try:
            project = Project(
                project_name=analysis.project_name,
                project_summary=analysis.project_summary,
                scope_and_deliverables=analysis.scope_and_deliverables,
                developer_tasks=analysis.developer_tasks,
                technology_stack=analysis.technology_stack,
                complexity_level=analysis.complexity_level,
                base_hours_required=analysis.time_estimation.get("base_hours_required"),
                total_hours_estimated=analysis.time_estimation.get("total_hours_estimated"),
                total_duration_weeks=analysis.time_estimation.get("total_duration_weeks"),
                total_duration_days=analysis.time_estimation.get("total_duration_days"),
                development_phase=analysis.time_estimation.get("development_phase"),
                testing_phase=analysis.time_estimation.get("testing_phase"),
                deployment_phase=analysis.time_estimation.get("deployment_phase"),
                buffer_included=analysis.time_estimation.get("buffer_included"),
                user_id=user_id,
                document_id=document.id
            )
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            return project.id
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create project record: {str(e)}")

   
    async def extract_technology_stack(self, document: Document) -> TechStackResponse:
        """Extract technology stack from document"""
        try:
            content = self._prepare_content(document)
            
            mistral_response = self._call_mistral_for_tech_extraction(content)
            tech_data = self._parse_tech_response(mistral_response)
            
            return TechStackResponse(
                success=True,
                message="Technology stack extracted successfully",
                detected_technologies=tech_data["detected_technologies"],
                recommended_technologies=tech_data["recommended_technologies"],
                technology_categories=tech_data["technology_categories"]
            )
            
        except Exception as e:
            return TechStackResponse(
                success=False,
                message="Technology extraction failed",
                error=str(e)
            )
    
    def _prepare_content(self, document: Document) -> str:
        """Prepare document content for tech extraction"""
        content = document.content
        if len(content) > 8000:
            content = content[:8000] + "..."
        return content
    
    def _call_mistral_for_tech_extraction(self, content: str) -> str:
        """Call Mistral API for technology stack extraction"""
        system_prompt = """You are a Technology Stack Analysis Assistant specialized in identifying and recommending technologies from project documents.

IMPORTANT: You must respond with ONLY valid JSON. Do not include any markdown, explanations, or additional text.

CORE CAPABILITIES:
1. Detect mentioned technologies in documents
2. Recommend suitable technologies based on project requirements
3. Categorize technologies by type
4. Provide technology alternatives

RESPONSE FORMAT REQUIREMENTS:
Respond with ONLY this exact JSON structure (no markdown, no explanations):
{
    "detected_technologies": ["list of technologies mentioned in document"],
    "recommended_technologies": ["list of recommended technologies based on project needs"],
    "technology_categories": {
        "frontend": ["frontend technologies"],
        "backend": ["backend technologies"], 
        "database": ["database technologies"],
        "cloud": ["cloud platforms"],
        "mobile": ["mobile technologies"],
        "tools": ["development tools"],
        "other": ["other technologies"]
    }
}"""

        user_prompt = f"""
Analyze the following document content and respond with ONLY valid JSON (no markdown, no explanations):

DOCUMENT CONTENT:
{content}

Extract mentioned technologies, recommend suitable ones, and categorize them. Return only the JSON response."""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
        }

        data = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }

        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions", 
                headers=headers, 
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Mistral API error: {response.text}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def _parse_tech_response(self, response: str) -> dict:
        """Parse Mistral response for technology data"""
        try:
            # Clean the response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, create a fallback response
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {response}")
            
            # Return a default structure with error info
            return {
                "detected_technologies": [],
                "recommended_technologies": ["React", "Node.js", "MongoDB", "Express.js"],
                "technology_categories": {
                    "frontend": ["React", "HTML", "CSS", "JavaScript"],
                    "backend": ["Node.js", "Express.js", "Python", "FastAPI"],
                    "database": ["MongoDB", "PostgreSQL", "MySQL"],
                    "cloud": ["AWS", "Google Cloud", "Azure"],
                    "mobile": ["React Native", "Flutter"],
                    "tools": ["Git", "Docker", "VS Code"],
                    "other": []
                }
            }