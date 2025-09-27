"""Webhook handling API routes."""

import os
import json
from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, SessionLocal
from services.webhook_service import WebhookService

router = APIRouter(prefix="/webhook", tags=["webhooks"])
webhook_service = WebhookService()


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None)
):
    """Handle incoming GitHub webhook events."""
    # Get raw payload
    payload = await request.body()
    
    # Verify signature if webhook secret is configured
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    if webhook_secret and x_hub_signature_256:
        if not webhook_service.verify_github_signature(
            payload, x_hub_signature_256, webhook_secret
        ):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
    
    # Parse JSON payload
    try:
        payload_json = json.loads(payload.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate payload structure
    if x_github_event:
        validation_result = webhook_service.validate_webhook_payload(
            payload_json, x_github_event
        )
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid payload: {', '.join(validation_result['errors'])}"
            )
    
    # Process the webhook event
    db = SessionLocal()
    try:
        result = await webhook_service.process_webhook_event(
            db, x_github_event or "unknown", payload_json
        )
        
        # Return result
        return {
            "status": "processed",
            "event_type": x_github_event,
            "delivery_id": x_github_delivery,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
    finally:
        db.close()


@router.get("/test")
async def test_webhook_endpoint():
    """Test endpoint to verify webhook URL is reachable."""
    return {
        "status": "ok",
        "message": "Webhook endpoint is reachable",
        "timestamp": "2025-01-27T19:50:00Z"
    }


@router.post("/test")
async def test_webhook_post():
    """Test POST endpoint for webhook connectivity tests."""
    return {
        "status": "ok",
        "message": "Webhook POST endpoint is working",
        "timestamp": "2025-01-27T19:50:00Z"
    }