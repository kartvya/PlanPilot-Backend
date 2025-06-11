from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth.auth import get_current_user
from app.models import User, Document, Project
from app.schemas import (
    ProjectRequest, 
    AnalysisResponse, 
    ProjectResponse, 
    ProjectSummaryResponse,
    DocumentResponse,
    DailyTaskRequest,
    DailyTaskResponse,
    TaskLogRequest
)
from app.service.document_service import DocumentService
from app.service.analysis_service import AnalysisService

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/upload-docs", response_model=AnalysisResponse)
async def upload_and_analyze_document(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    daily_hours: int = Form(8),
    working_days_per_week: int = Form(5),
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
            working_days_per_week=working_days_per_week
        )
        
        analysis_result = await analysis_service.analyze_project(
            document, project_request, current_user.id
        )
        
        if analysis_result.success:
            return AnalysisResponse(
                success=True,
                message="Document uploaded and analyzed successfully",
                analysis=analysis_result.analysis,
                project_id=analysis_result.project_id
            )
        else:
            return analysis_result
            
    except Exception as e:
        return AnalysisResponse(
            success=False,
            message="Upload and analysis failed",
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


# Add these new endpoints to the router
@router.post("/start-project", response_model=DailyTaskResponse)
async def start_project_plan(
    request: DailyTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize project timeline and get first day's tasks"""
    try:
        project = db.query(Project).filter(
            Project.id == request.project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get the initial plan from analysis service
        analysis_service = AnalysisService(db)
        day_plan = await analysis_service.generate_day_plan(
            project_id=request.project_id,
            start_date=request.start_date,
            day_number=1
        )
        
        return day_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start project: {str(e)}"
        )

@router.post("/log-tasks", response_model=DailyTaskResponse)
async def log_daily_tasks(
    request: TaskLogRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log completed tasks and get next day's plan"""
    try:
        project = db.query(Project).filter(
            Project.id == request.project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        analysis_service = AnalysisService(db)
        
        # Save the completed tasks
        await analysis_service.log_completed_tasks(
            project_id=request.project_id,
            day_number=request.day_number,
            completed_hours=request.completed_hours
        )
        
        # Get the next day's plan
        next_day_plan = await analysis_service.generate_day_plan(
            project_id=request.project_id,
            day_number=request.day_number + 1
        )
        
        return next_day_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log tasks: {str(e)}"
        )

@router.get("/current-day-plan/{project_id}", response_model=DailyTaskResponse)
async def get_current_day_plan(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current day's task plan"""
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
        
        analysis_service = AnalysisService(db)
        day_plan = await analysis_service.get_current_day_plan(
            project_id=project_id
        )
        
        return day_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current day plan: {str(e)}"
        )


@router.delete("/project/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a project"""
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
        
        db.delete(project)
        db.commit()
        
        return {"success": True, "message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )

@router.get("/documents", response_model=List[DocumentResponse])
async def get_user_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for the current user"""
    try:
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        return [DocumentResponse.from_orm(doc) for doc in documents]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(e)}"
        )