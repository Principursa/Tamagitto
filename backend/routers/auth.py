"""Authentication API routes."""

from typing import Optional
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.user import User
from services.auth_service import AuthService
from services.github_service import GitHubService

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
auth_service = AuthService()
github_service = GitHubService()


class GitHubCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


@router.get("/github")
async def github_auth_url():
    """Get GitHub OAuth authorization URL."""
    client_id = github_service.client_id
    if not client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&scope=public_repo,user:email"
        f"&state=tamagitto_auth"
    )
    
    return {
        "auth_url": auth_url,
        "client_id": client_id
    }


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str = None,
    http_request: Request = None,
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    try:
        # Exchange code for token and user info
        github_data = await github_service.exchange_code_for_token(code)
        access_token = github_data["access_token"]
        github_user = github_data["user"]
        
        # Check if user exists
        github_id = str(github_user["id"])
        user = db.query(User).filter(User.github_id == github_id).first()
        
        if not user:
            # Create new user
            user = User.create_from_github(github_user, access_token)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update existing user's token and info
            user.encrypt_token(access_token)
            user.username = github_user["login"]
            user.email = github_user.get("email")
            user.avatar_url = github_user.get("avatar_url")
            user.update_last_active()
            db.commit()
        
        # Create JWT tokens
        jwt_access_token = auth_service.create_access_token(user.id)
        jwt_refresh_token = auth_service.create_refresh_token(user.id)
        
        # Create user session
        user_agent = http_request.headers.get("User-Agent")
        client_ip = http_request.client.host if http_request.client else None
        
        auth_service.create_user_session(
            db, user, jwt_refresh_token, user_agent, client_ip
        )
        
        # Return success page with tokens that the extension can capture
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                       text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       color: white; margin: 0; }}
                .container {{ max-width: 400px; margin: 0 auto; background: rgba(255,255,255,0.1);
                            padding: 40px; border-radius: 20px; }}
                h1 {{ margin-bottom: 20px; }}
                .success {{ color: #10b981; font-size: 60px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>Authentication Successful!</h1>
                <p>You can now close this tab and return to the Tamagitto extension.</p>
                <script>
                    // Store tokens for extension to access
                    window.tamagittoAuth = {json.dumps({
                        "access_token": jwt_access_token,
                        "refresh_token": jwt_refresh_token,
                        "user": user.to_dict()
                    })};

                    // Try to close the tab after 2 seconds
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                </script>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    result = auth_service.refresh_access_token(db, request.refresh_token)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    return result


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Logout user and revoke tokens."""
    token = credentials.credentials
    user_id = auth_service.get_user_id_from_token(token)
    
    if user_id:
        # Revoke all user sessions
        revoked_count = auth_service.revoke_all_user_sessions(db, user_id)
        return {
            "message": "Logged out successfully",
            "sessions_revoked": revoked_count
        }
    
    return {"message": "Logged out"}


@router.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information."""
    token = credentials.credentials
    user_id = auth_service.get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Update last active
    user.update_last_active()
    db.commit()
    
    return user.to_dict()


@router.get("/sessions")
async def get_user_sessions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get user's active sessions."""
    token = credentials.credentials
    user_id = auth_service.get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    sessions = auth_service.get_user_sessions(db, user_id, active_only=True)
    
    return {
        "sessions": [session.to_dict() for session in sessions],
        "total_active": len(sessions)
    }


async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    user_id = auth_service.get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user