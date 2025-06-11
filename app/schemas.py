from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional, Union
from datetime import date, datetime

# User schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Document schemas
class DocumentCreate(BaseModel):
    filename: str
    content: str
    file_type: str
    file_size: int

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Project schemas
class ProjectRequest(BaseModel):
    project_name: Optional[str] = None
    daily_hours: int = 8
    working_days_per_week: int = 5

class ProjectAnalysis(BaseModel):
    project_name: str
    project_summary: str
    scope_and_deliverables: str
    time_estimation: Dict[str, str]
    developer_tasks: List[str]
    technology_stack: List[str]
    complexity_level: str

class ProjectResponse(BaseModel):
    id: int
    project_name: str
    project_summary: str
    scope_and_deliverables: str
    developer_tasks: List[str]
    technology_stack: List[str]
    complexity_level: str
    base_hours_required: Optional[str]
    total_hours_estimated: Optional[str]
    total_duration_weeks: Optional[str]
    total_duration_days: Optional[str]
    development_phase: Optional[str]
    testing_phase: Optional[str]
    deployment_phase: Optional[str]
    buffer_included: Optional[str]
    created_at: datetime
    document: DocumentResponse
    
    class Config:
        from_attributes = True

class ProjectSummaryResponse(BaseModel):
    id: int
    project_name: str
    project_summary: str
    complexity_level: str
    total_duration_weeks: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# API Response schemas
class AnalysisResponse(BaseModel):
    success: bool
    message: str
    analysis: Optional[ProjectAnalysis] = None
    project_id: Optional[int] = None
    error: Optional[str] = None

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None



# Add these new schemas (can be in schemas.py)
class DailyTaskRequest(BaseModel):
    start_date: date
    project_id: int

class TaskLogRequest(BaseModel):
    project_id: int
    day_number: int
    completed_hours: Dict[str, float]  # task_name: hours_completed

class DailyTaskResponse(BaseModel):
    day: str
    date: date
    planned_hours: float
    tasks: List[Dict[str, Union[str, float]]]
    carryover_from_previous_days: List[str]
    message: Optional[str] = None