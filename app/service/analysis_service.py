from datetime import date, timedelta, datetime
import re
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import json
import requests
import os
from dotenv import load_dotenv

from app.models import Document, Project
from app.schemas import ProjectRequest, ProjectAnalysis, AnalysisResponse
from app.service.document_service import DocumentService

load_dotenv()

class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_service = DocumentService(db)
    
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
            5. Technology recommendations
            6. Project complexity assessment
            
            Include 1.5x buffer multiplier for realistic human work estimation.
            """
            
            mistral_response = self._call_mistral_api(
                analysis_prompt, 
                analysis_content, 
                project_request.project_name, 
                project_request.daily_hours, 
                project_request.working_days_per_week
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
    
    def _call_mistral_api(self, prompt: str, document_context: str, project_name: Optional[str] = None, daily_hours: int = 8, working_days_per_week: int = 5) -> str:
        """Call Mistral API for project analysis"""
        
        buffer_multiplier = 1.5
        
        system_prompt = f"""You are an expert Project Analysis Assistant specialized in software development project estimation and planning.

CORE CAPABILITIES:
1. Project Requirements Analysis
2. Scope & Deliverables Identification  
3. Realistic Time & Resource Planning with Human Buffer
4. Work Estimation & Task Breakdown

ANALYSIS RULES:
- FIRST calculate the BASE hours needed for the project (without buffer)
- THEN apply the {buffer_multiplier}x buffer to get REALISTIC hours
- FINALLY calculate duration based on REALISTIC hours and working schedule
- Duration should DECREASE if daily hours increase (same total work spread over fewer days)
- Total realistic hours should stay CONSTANT regardless of schedule
- ONLY analyze based on the provided document context
- If document context is insufficient, state "Insufficient information in document for complete analysis"
- Provide specific, actionable insights
- Be realistic in estimations with human buffer included
- Consider modern development practices

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
}}

ESTIMATION METHODOLOGY:
1. Calculate BASE hours needed (without buffer)
2. Apply {buffer_multiplier}x buffer: realistic_hours = base_hours * {buffer_multiplier}
3. Calculate duration:
   - working_hours_per_week = {daily_hours} * {working_days_per_week}
   - total_weeks = realistic_hours / working_hours_per_week
   - total_days = realistic_hours / {daily_hours}
"""

        project_context = f"Project Name: {project_name}" if project_name else "Please generate an appropriate project name based on the document content."

        user_prompt = f"""
ANALYSIS REQUEST: {prompt}

{project_context}

WORK PARAMETERS:
- Daily Hours: {daily_hours}
- Working Days/Week: {working_days_per_week}
- Buffer Multiplier: {buffer_multiplier}x (for realistic human work estimation)

DOCUMENT CONTENT:
{document_context}

Please analyze this project document and:
1. First estimate the BASE hours required (without buffer)
2. Then calculate REALISTIC hours by applying {buffer_multiplier}x buffer
3. Finally calculate duration based on REALISTIC hours and the work schedule
4. Ensure total realistic hours stay constant regardless of schedule
5. Show duration decreases when daily hours increase
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
    
    def _parse_mistral_response(self, response_text: str) -> ProjectAnalysis:
        """Parse Mistral API response and convert to ProjectAnalysis model"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Find JSON in the response
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
        
        
    async def generate_day_plan(self, project_id: int, start_date: str = None, day_number: int = 1):
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception("Project not found")

        def extract_int(value, default=4):
            if not value:
                return default
            if isinstance(value, int):
                return value
            match = re.search(r"\d+", str(value))
            return int(match.group()) if match else default

        # Parse tasks
        tasks = project.developer_tasks or []
        if isinstance(tasks, str):
            import json
            tasks = json.loads(tasks)
        if tasks and isinstance(tasks[0], str):
            tasks = [{"task": t, "estimated_hours": 1} for t in tasks]

        daily_hours = extract_int(project.base_hours_required, 4)
        working_days_per_week = extract_int(project.total_duration_days, 5)

        # --- FIX: Handle both str and date for start_date ---
        if start_date:
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            elif isinstance(start_date, date):
                start_dt = datetime.combine(start_date, datetime.min.time())
            else:
                raise Exception("Invalid start_date type")
        elif project.start_date:
            if isinstance(project.start_date, str):
                start_dt = datetime.strptime(project.start_date, "%Y-%m-%d")
            elif isinstance(project.start_date, date):
                start_dt = datetime.combine(project.start_date, datetime.min.time())
            else:
                raise Exception("Invalid project.start_date type")
        else:
            start_dt = datetime.utcnow()
        # Only count working days
        current_date = start_dt
        days_added = 1
        while days_added < day_number:
            current_date += timedelta(days=1)
            if current_date.weekday() < working_days_per_week:
                days_added += 1

        # Get carryover from previous days
        completion_log = project.completion_log or []
        completed_tasks = set()
        carryover = []
        for log in completion_log:
            for t in log.get('completed_tasks', []):
                completed_tasks.add(t['task'])
            for c in log.get('carryover', []):
                carryover.append(c)

        # Assign tasks for today
        today_tasks = []
        hours_left = daily_hours
        carryover_today = []

        # Flatten all tasks, skipping completed
        pending_tasks = [t for t in tasks if t['task'] not in completed_tasks]

        for t in pending_tasks:
            est = t.get('estimated_hours', 1)
            if est <= hours_left:
                today_tasks.append({"task": t['task'], "estimated_hours": est})
                hours_left -= est
            else:
                if hours_left > 0:
                    today_tasks.append({"task": t['task'], "estimated_hours": hours_left})
                    carryover_today.append(f"{t['task']} ({est-hours_left} hour(s) left)")
                    hours_left = 0
                else:
                    carryover_today.append(f"{t['task']} ({est} hour(s))")

        return {
            "day": f"Day {day_number}",
            "date": current_date.strftime("%Y-%m-%d"),
            "planned_hours": daily_hours,
            "tasks": today_tasks,
            "carryover_from_previous_days": carryover,
            "message": f"Plan for Day {day_number} - {current_date.strftime('%A, %B %d, %Y')}"
        }

    async def log_completed_tasks(self, project_id: int, day_number: int, completed_hours: int):
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception("Project not found")
        log = project.completion_log or []
        log.append({
            "day": day_number,
            "completed_hours": completed_hours,
            "completed_tasks": [],  # You can expand this to log actual tasks
            "carryover": []         # You can expand this to log actual carryover
        })
        project.completion_log = log
        project.current_day = day_number + 1
        self.db.commit()
        return True

    async def get_current_day_plan(self, project_id: int):
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception("Project not found")
        return await self.generate_day_plan(
            project_id=project_id,
            day_number=project.current_day or 1
        )

    def _parse_tasks_from_project(self, project: Project) -> List[Dict]:
        """Parse tasks from project's developer_tasks"""
        tasks = []
        if not project.developer_tasks:
            return tasks
            
        for task_str in project.developer_tasks:
            # Parse task string like "Task: Design UI (4 hours)"
            try:
                if ":" in task_str and "(" in task_str:
                    # Format: "Task: Description (X hours)"
                    desc_part, hours_part = task_str.split("(")
                    description = desc_part.split(":", 1)[1].strip()
                    hours = float(hours_part.split(" ")[0])
                elif "-" in task_str:
                    # Format: "Description - X hours"
                    description, hours_part = task_str.split("-", 1)
                    hours = float(hours_part.split(" ")[1])
                else:
                    # Fallback format
                    description = task_str
                    hours = 2.0  # Default estimate
                    
                tasks.append({
                    "description": description,
                    "estimated_hours": hours
                })
            except Exception:
                continue
                
        return tasks

    def _get_completed_tasks(self, project_id: int) -> Dict[str, float]:
        """Get all completed tasks from project logs"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.completion_log:
            return {}
            
        completed = {}
        for day_log in project.completion_log:
            for task, hours in day_log.get('completed_tasks', {}).items():
                if task in completed:
                    completed[task] += hours
                else:
                    completed[task] = hours
                    
        return completed

    def _calculate_remaining_tasks(
        self,
        all_tasks: List[Dict],
        completed_tasks: Dict[str, float]
    ) -> List[Dict]:
        """Calculate remaining tasks based on completion"""
        remaining = []
        
        for task in all_tasks:
            task_desc = task['description']
            task_hours = task['estimated_hours']
            
            completed_hours = completed_tasks.get(task_desc, 0)
            remaining_hours = task_hours - completed_hours
            
            if remaining_hours > 0:
                remaining.append({
                    "description": task_desc,
                    "estimated_hours": remaining_hours
                })
                
        return remaining

    def _calculate_carryover_tasks(self, project_id: int, day_number: int) -> List[Dict]:
        """Calculate tasks that need to be carried over from previous days"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.completion_log:
            return []
            
        # Get all tasks from project
        all_tasks = self._parse_tasks_from_project(project)
        
        # Get completed tasks up to previous day
        completed_tasks = {}
        for day_log in project.completion_log:
            if day_log.get('day_number', 0) <= day_number:
                for task, hours in day_log.get('completed_tasks', {}).items():
                    if task in completed_tasks:
                        completed_tasks[task] += hours
                    else:
                        completed_tasks[task] = hours
        
        # Calculate remaining tasks
        return self._calculate_remaining_tasks(all_tasks, completed_tasks)
    
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