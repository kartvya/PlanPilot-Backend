from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.auth.auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserResponse, StandardResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=StandardResponse)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return StandardResponse(
            success=True,
            message="User registered successfully",
            data={"username": new_user.username, "email": new_user.email}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    try:
        user = authenticate_user(db, user_credentials.username, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

# @router.get("/me", response_model=UserResponse)
# async def get_current_user_info(current_user: User = Depends(get_current_user)):
#     """Get current user information"""
#     return UserResponse.from_orm(current_user)