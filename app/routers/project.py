from datetime import datetime
import json
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.auth.auth import get_current_user
from app.models import DailyLog, User, Document, Project
from app.schemas import (
    ProjectAnalysis,
    ProjectRequest, 
    AnalysisResponse,
    ProjectRequestWithTech, 
    ProjectResponse, 
    ProjectSummaryResponse,
    TechStackResponse
)
from app.service.document_service import DocumentService
from app.service.analysis_service import AnalysisService

router = APIRouter(prefix="/projects", tags=["Projects"])

# @router.post("/upload-docs", response_model=AnalysisResponse)
# async def upload_and_analyze_document(
#     file: UploadFile = File(...),
#     project_name: Optional[str] = Form(None),
#     daily_hours: int = Form(8),
#     working_days_per_week: int = Form(5),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Upload document and analyze project"""
#     try:
#         if not file.filename.endswith(('.pdf', '.txt')):
#             return AnalysisResponse(
#                 success=False,
#                 message="Invalid file type",
#                 error="Only PDF and TXT files are supported"
#             )
        
#         doc_service = DocumentService(db)
#         analysis_service = AnalysisService(db)
        
#         document = await doc_service.process_document(file, current_user.id)
        
#         if not document:
#             return AnalysisResponse(
#                 success=False,
#                 message="Document processing failed",
#                 error="Could not process the uploaded document"
#             )
        
#         project_request = ProjectRequest(
#             project_name=project_name,
#             daily_hours=daily_hours,
#             working_days_per_week=working_days_per_week
#         )
        
#         analysis_result = await analysis_service.analyze_project(
#             document, project_request, current_user.id
#         )
        
#         if analysis_result.success:
#             return AnalysisResponse(
#                 success=True,
#                 message="Document uploaded and analyzed successfully",
#                 analysis=analysis_result.analysis,
#                 project_id=analysis_result.project_id
#             )
#         else:
#             return analysis_result
            
#     except Exception as e:
#         return AnalysisResponse(
#             success=False,
#             message="Upload and analysis failed",
#             error=str(e)
#         )


@router.post("/upload-docs", response_model=AnalysisResponse)
async def upload_and_analyze_document(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    daily_hours: int = Form(8),
    working_days_per_week: int = Form(5),
    technologies: Optional[List[str]] = Form(None),  # NEW PARAM
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document and analyze project"""
    try:
        if not file.filename.endswith(('.pdf', '.txt')):
            return AnalysisResponse(
                success=False,
                message="Invalid file type",
                error="Only PDF and TXT files are supported"
            )
        
        doc_service = DocumentService(db)
        analysis_service = AnalysisService(db)
        
        document = await doc_service.process_document(file, current_user.id)
        
        if not document:
            return AnalysisResponse(
                success=False,
                message="Document processing failed",
                error="Could not process the uploaded document"
            )
        
        project_request = ProjectRequest(
            project_name=project_name,
            daily_hours=daily_hours,
            working_days_per_week=working_days_per_week,
            technologies=technologies  # <-- include technologies here
        )
        
        analysis_result = await analysis_service.analyze_project(
            document, project_request, current_user.id
        )
        
        return analysis_result
            
    except Exception as e:
        return AnalysisResponse(
            success=False,
            message="Upload and analysis failed",
            error=str(e)
        )


@router.post("/extract-tech-stack", response_model=TechStackResponse)
async def extract_technology_stack(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract technology stack from uploaded document"""
    try:
        if not file.filename.endswith(('.pdf', '.txt')):
            return TechStackResponse(
                success=False,
                message="Invalid file type",
                error="Only PDF and TXT files are supported"
            )
        
        doc_service = DocumentService(db)
        tech_service = AnalysisService(db)
        
        document = await doc_service.process_document(file, current_user.id)
        
        if not document:
            return TechStackResponse(
                success=False,
                message="Document processing failed",
                error="Could not process the uploaded document"
            )
        
        tech_stack_result = await tech_service.extract_technology_stack(document)
        
        return tech_stack_result
            
    except Exception as e:
        return TechStackResponse(
            success=False,
            message="Technology stack extraction failed",
            error=str(e)
        )

@router.get("/my-projects", response_model=List[ProjectSummaryResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all projects for the current user"""
    try:
        projects = db.query(Project).filter(Project.user_id == current_user.id).all()
        
        project_summaries = []
        for project in projects:
            project_summaries.append(ProjectSummaryResponse(
                id=project.id,
                project_name=project.project_name,
                project_summary=project.project_summary,
                complexity_level=project.complexity_level,
                total_duration_weeks=project.total_duration_weeks,
                created_at=project.created_at
            ))
        
        return project_summaries
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=ProjectResponse)
async def get_project_details(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed project information"""
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project details: {str(e)}"
        )
    
@router.post("/generate-daily-tasks", response_model=dict)
async def generate_daily_tasks(
    project_id: int = Form(...),
    target_date: str = Form(...),
    day_number: int = Form(...),
    daily_hours: int = Form(8),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()

        if not project:
            return {
                "success": False,
                "message": "Project not found",
                "error": "Project does not exist or access denied"
            }

        project_analysis = {
            "project_name": project.project_name,
            "project_summary": project.project_summary,
            "scope_and_deliverables": project.scope_and_deliverables,
            "time_estimation": {
                "base_hours_required": project.base_hours_required,
                "total_hours_estimated": project.total_hours_estimated,
                "total_duration_weeks": project.total_duration_weeks,
                "total_duration_days": project.total_duration_days,
                "development_phase": project.development_phase,
                "testing_phase": project.testing_phase,
                "deployment_phase": project.deployment_phase,
                "buffer_included": project.buffer_included
            },
            "developer_tasks": project.developer_tasks,
            "technology_stack": project.technology_stack,
            "complexity_level": project.complexity_level
        }

        analysis_service = AnalysisService(db)
        daily_task_response = analysis_service._call_mistral_api_for_daily_tasks(
            project_analysis=project_analysis,
            target_date=target_date,
            day_number=day_number,
            daily_hours=daily_hours
        )

        response_text = daily_task_response.strip()
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            return {
                "success": False,
                "message": "Failed to parse daily tasks response",
                "error": "No JSON found in Mistral response"
            }

        json_str = response_text[json_start:json_end]
        daily_tasks = json.loads(json_str)

        # Ensure all new tasks have `task_done: False`
        for task in daily_tasks.get("tasks", []):
            task["task_done"] = False

        # --- NEW: Fetch and merge carryover tasks ---
        if day_number > 1:
            previous_log = db.query(DailyLog).filter_by(
                project_id=project.id,
                user_id=current_user.id,
                day_number=day_number - 1
            ).first()

            if previous_log and previous_log.tasks:
                for task in previous_log.tasks:
                    if not task.get("task_done"):
                        # Ensure structure matches expected
                        carryover_task = {
                            "task": task["task"],
                            "estimated_hours": task["estimated_hours"],
                            "task_done": False
                        }
                        daily_tasks["tasks"].append(carryover_task)

        # Final task list
        final_tasks = daily_tasks["tasks"]

        # Save or update today's log
        existing_log = db.query(DailyLog).filter_by(
            project_id=project.id,
            user_id=current_user.id,
            day_number=day_number
        ).first()

        if existing_log:
            existing_log.tasks = final_tasks
            existing_log.planned_hours = daily_hours
            existing_log.target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            new_log = DailyLog(
                project_id=project.id,
                user_id=current_user.id,
                day_number=day_number,
                target_date=datetime.strptime(target_date, "%Y-%m-%d").date(),
                planned_hours=daily_hours,
                tasks=final_tasks
            )
            db.add(new_log)

        db.commit()

        return {
            "success": True,
            "message": "Daily tasks generated and saved successfully",
            "daily_tasks": {
                "day": f"Day {day_number}",
                "date": target_date,
                "planned_hours": daily_hours,
                "tasks": final_tasks
            }
        }

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return {
            "success": False,
            "message": "Failed to parse daily tasks response",
            "error": f"JSON parsing error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Daily task generation failed",
            "error": str(e)
        }



@router.post("/projects/log-daily-tasks", response_model=dict)
async def log_daily_tasks(
    project_id: int = Body(...),
    day_number: int = Body(...),
    completed_tasks: List[Dict[str, Any]] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        daily_log = db.query(DailyLog).filter(
            DailyLog.project_id == project_id,
            DailyLog.user_id == current_user.id,
            DailyLog.day_number == day_number
        ).first()

        if not daily_log:
            return {
                "success": False,
                "message": "Daily log not found for this project/day",
                "error": "No matching daily log"
            }

        completed_set = {(t["task"], t["estimated_hours"]) for t in completed_tasks}

        task_list = daily_log.tasks

        updated_tasks = []
        for task in task_list:
            task_key = (task["task"], task["estimated_hours"])
            task["task_done"] = task_key in completed_set
            updated_tasks.append(task)

        daily_log.tasks = updated_tasks
        flag_modified(daily_log, "tasks")
        db.add(daily_log)
        db.commit()

        return {
            "success": True,
            "message": "Tasks updated successfully",
            "completed_count": sum(t["task_done"] for t in updated_tasks),
            "remaining_count": sum(not t["task_done"] for t in updated_tasks),
            "total": len(updated_tasks)
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": "Failed to update tasks",
            "error": str(e)
        }


@router.get("/daily-log", response_model=dict)
async def get_daily_log(
    project_id: int,
    day_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    daily_log = db.query(DailyLog).filter_by(
        project_id=project_id,
        user_id=current_user.id,
        day_number=day_number
    ).first()

    if not daily_log:
        return {"success": False, "message": "Log not found"}

    return {
        "success": True,
        "log": {
            "date": daily_log.target_date,
            "planned_hours": daily_log.planned_hours,
            "tasks": daily_log.tasks
        }
    }
