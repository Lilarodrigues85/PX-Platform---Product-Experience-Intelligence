# US-002: API de Ingestão de Eventos
# FastAPI endpoint para receber eventos em lote

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import json
import time
from datetime import datetime

app = FastAPI(title="PX Platform Events API", version="1.0.0")

# Models
class Event(BaseModel):
    event: str = Field(..., description="Event name")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Event properties")

class EventBatch(BaseModel):
    events: List[Event] = Field(..., description="List of events")

class EventResponse(BaseModel):
    success: bool
    events_received: int
    processing_id: str
    estimated_processing_time: str = "5s"

# Rate limiting storage (in production use Redis)
rate_limits = {}

# Authentication & Rate Limiting
async def get_tenant_id(
    authorization: str = Header(...),
    x_px_project_id: str = Header(..., alias="X-PX-Project-ID")
) -> str:
    """Extract tenant ID from JWT token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    # In production: decode JWT and extract tenant_id
    # For now, use project_id as tenant_id
    tenant_id = x_px_project_id
    
    # Rate limiting check
    current_time = time.time()
    if tenant_id not in rate_limits:
        rate_limits[tenant_id] = {"count": 0, "window_start": current_time}
    
    rate_data = rate_limits[tenant_id]
    
    # Reset window if needed (1 hour window)
    if current_time - rate_data["window_start"] > 3600:
        rate_data["count"] = 0
        rate_data["window_start"] = current_time
    
    # Check rate limit (10000 requests per hour for pro tier)
    if rate_data["count"] >= 10000:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": "10000",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(rate_data["window_start"] + 3600))
            }
        )
    
    rate_data["count"] += 1
    return tenant_id

# Event validation
def validate_event(event: Event, tenant_id: str) -> Dict[str, Any]:
    """Validate and enrich event data"""
    validated_event = {
        "event_id": f"evt_{int(time.time() * 1000)}_{hash(str(event))}",
        "tenant_id": tenant_id,
        "event_name": event.event,
        "user_id": event.user_id,
        "session_id": event.session_id,
        "timestamp": event.timestamp or datetime.utcnow().isoformat(),
        "properties": event.properties,
        "ingested_at": datetime.utcnow().isoformat(),
        "version": 1
    }
    
    # Basic validation
    if not event.event:
        raise HTTPException(status_code=400, detail="Event name is required")
    
    if len(event.event) > 100:
        raise HTTPException(status_code=400, detail="Event name too long")
    
    return validated_event

# Queue simulation (in production use Kafka)
event_queue = []

async def queue_events(events: List[Dict[str, Any]]):
    """Queue events for processing"""
    event_queue.extend(events)

def generate_processing_id() -> str:
    """Generate unique processing ID"""
    return f"proc_{int(time.time())}_{hash(str(time.time()))}"

# Main endpoint
@app.post("/api/v1/events/batch", response_model=EventResponse)
async def ingest_events(
    batch: EventBatch,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Ingest batch of events for processing
    
    - **events**: List of events to process
    - **Returns**: Processing confirmation with ID
    """
    
    if not batch.events:
        raise HTTPException(status_code=400, detail="No events provided")
    
    if len(batch.events) > 1000:
        raise HTTPException(status_code=400, detail="Too many events in batch (max 1000)")
    
    # Validate all events
    validated_events = []
    for event in batch.events:
        try:
            validated_event = validate_event(event, tenant_id)
            validated_events.append(validated_event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid event: {str(e)}")
    
    # Queue for async processing
    processing_id = generate_processing_id()
    background_tasks.add_task(queue_events, validated_events)
    
    return EventResponse(
        success=True,
        events_received=len(validated_events),
        processing_id=processing_id
    )

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Queue status (for monitoring)
@app.get("/api/v1/events/queue/status")
async def queue_status():
    """Get current queue status"""
    return {
        "queue_size": len(event_queue),
        "status": "processing" if event_queue else "idle"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)