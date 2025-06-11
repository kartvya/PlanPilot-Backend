from sqlalchemy import Column, Date, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_type = Column(String(10), nullable=False) 
    file_size = Column(Integer, nullable=False) 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(JSON, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    document = relationship("Document", back_populates="chunks")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(255), nullable=False)
    project_summary = Column(Text, nullable=False)
    scope_and_deliverables = Column(Text, nullable=False)
    developer_tasks = Column(JSON, nullable=False) 
    technology_stack = Column(JSON, nullable=False)  
    complexity_level = Column(String(50), nullable=False)
    
    base_hours_required = Column(String(100), nullable=True)
    total_hours_estimated = Column(String(100), nullable=True)
    total_duration_weeks = Column(String(100), nullable=True)
    total_duration_days = Column(String(100), nullable=True)
    development_phase = Column(String(100), nullable=True)
    testing_phase = Column(String(100), nullable=True)
    deployment_phase = Column(String(100), nullable=True)
    buffer_included = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    completion_log = Column(JSON, default=list)
    current_day = Column(Integer, default=1) 
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="projects")
    document = relationship("Document", back_populates="projects")