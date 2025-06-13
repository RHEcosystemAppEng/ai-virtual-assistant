import os
import base64
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from pydantic import BaseModel
from sqlalchemy.future import select
from backend import schemas
from backend.database import get_db
from backend.models import User as UserModel, RoleEnum
from backend.schemas import UserRead

class TokenData(BaseModel):
    email: str | None = None

async def get_current_user(_oauth_proxy: str = Cookie(None, alias="_oauth_proxy"), db=Depends(get_db)):
    if not _oauth_proxy:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    try:
        # Decode the base64 cookie value
        decoded = base64.b64decode(_oauth_proxy).decode('utf-8')
        # The cookie value should be the email address
        email = decoded.strip()
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication cookie",
            )

        result = await db.execute(select(UserModel).filter(UserModel.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except (base64.binascii.Error, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication cookie format",
        )

class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: UserRead = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have the right privileges",
            )
        return user

async def get_or_create_user_from_token(_oauth_proxy: str = Cookie(None, alias="_oauth_proxy"), db=Depends(get_db)):
    if not _oauth_proxy:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    try:
        # Decode the base64 cookie value
        decoded = base64.b64decode(_oauth_proxy).decode('utf-8')
        # The cookie value should be the email address
        email = decoded.strip()
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication cookie",
            )

        result = await db.execute(select(UserModel).filter(UserModel.email == email))
        user = result.scalar_one_or_none()
        
        if user is None:
            # Create new user with default role
            new_user = UserModel(
                email=email,
                role=RoleEnum.user,
                username=email  # Using email as username for now
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            user = new_user

        return user

    except (base64.binascii.Error, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication cookie format",
        )

auth_router = APIRouter(prefix="/api/v1", tags=["auth"])

@auth_router.get("/login", response_model=schemas.UserRead)
async def login(current_user: schemas.UserRead = Depends(get_or_create_user_from_token)):
    return current_user 