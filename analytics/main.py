"""
Executive Safety Dashboard - Analytics Service
Enterprise-grade data processing and machine learning service for safety analytics
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GzipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis.asyncio as redis
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server

from config import settings
from database import Database
from models.safety_models import SafetyPredictionModel, IncidentAnalysisModel
from services.analytics_service import AnalyticsService
from services.prediction_service import PredictionService
from services.report_service import ReportService
from utils.logger import setup_logging
from utils.metrics import MetricsCollector

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('analytics_requests_total', 'Total analytics requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('analytics_request_duration_seconds', 'Request duration')
PREDICTION_COUNT = Counter('safety_predictions_total', 'Total safety predictions', ['type'])
MODEL_ACCURACY = Histogram('model_accuracy_score', 'Model accuracy scores', ['model_type'])

# Global services
db: Optional[Database] = None
redis_client: Optional[redis.Redis] = None
analytics_service: Optional[AnalyticsService] = None
prediction_service: Optional[PredictionService] = None
report_service: Optional[ReportService] = None

# Pydantic models
class SafetyIncident(BaseModel):
    incident_id: str
    timestamp: datetime
    severity: str = Field(..., regex="^(low|medium|high|critical)$")
    category: str
    description: str
    location: str
    employee_id: Optional[str] = None
    cost_estimate: Optional[float] = None
    metadata: Optional[Dict] = {}

class AnalyticsRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    metrics: List[str] = Field(default=["incidents", "costs", "trends"])
    filters: Optional[Dict] = {}

class PredictionRequest(BaseModel):
    prediction_type: str = Field(..., regex="^(incident_risk|cost_forecast|safety_score)$")
    time_horizon: int = Field(default=30, ge=1, le=365)
    parameters: Optional[Dict] = {}

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    uptime: float
    version: str
    services: Dict[str, str]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db, redis_client, analytics_service, prediction_service, report_service
    
    logger.info("Starting Executive Safety Dashboard Analytics Service")
    
    # Initialize database connection
    db = Database(settings.database_url)
    await db.connect()
    logger.info("Database connected")
    
    # Initialize Redis connection
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.ping()
    logger.info("Redis connected")
    
    # Initialize services
    analytics_service = AnalyticsService(db, redis_client)
    prediction_service = PredictionService(db, redis_client)
    report_service = ReportService(db, redis_client)
    
    # Start background tasks
    asyncio.create_task(background_model_training())
    asyncio.create_task(background_metrics_collection())
    
    # Start Prometheus metrics server
    start_http_server(8001)
    logger.info("Prometheus metrics server started on port 8001")
    
    logger.info("Analytics service initialization completed")
    
    yield
    
    # Cleanup
    logger.info("Shutting down analytics service")
    await redis_client.close()
    await db.disconnect()
    logger.info("Analytics service shutdown completed")

# Initialize FastAPI app
app = FastAPI(
    title="Executive Safety Dashboard Analytics API",
    description="Enterprise-grade safety analytics and machine learning service",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GzipMiddleware, minimum_size=1000)

# Dependency injection
async def get_analytics_service() -> AnalyticsService:
    if analytics_service is None:
        raise HTTPException(status_code=503, detail="Analytics service not available")
    return analytics_service

async def get_prediction_service() -> PredictionService:
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    return prediction_service

async def get_report_service() -> ReportService:
    if report_service is None:
        raise HTTPException(status_code=503, detail="Report service not available")
    return report_service

# Background tasks
async def background_model_training():
    """Background task for periodic model training"""
    while True:
        try:
            logger.info("Starting scheduled model training")
            if prediction_service:
                await prediction_service.retrain_models()
            logger.info("Scheduled model training completed")
        except Exception as e:
            logger.error(f"Model training failed: {e}")
        
        # Wait for next training cycle (24 hours)
        await asyncio.sleep(86400)

async def background_metrics_collection():
    """Background task for metrics collection"""
    while True:
        try:
            if analytics_service:
                await analytics_service.collect_system_metrics()
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
        
        # Collect metrics every 5 minutes
        await asyncio.sleep(300)

# Health endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for container monitoring"""
    try:
        # Check database
        db_status = "connected" if db and await db.health_check() else "disconnected"
        
        # Check Redis
        redis_status = "connected"
        try:
            if redis_client:
                await redis_client.ping()
        except:
            redis_status = "disconnected"
        
        return HealthResponse(
            status="healthy" if db_status == "connected" and redis_status == "connected" else "unhealthy",
            timestamp=datetime.utcnow(),
            uptime=0.0,  # Will be calculated by actual uptime
            version="1.0.0",
            services={
                "database": db_status,
                "redis": redis_status,
                "analytics": "available" if analytics_service else "unavailable",
                "prediction": "available" if prediction_service else "unavailable",
                "reporting": "available" if report_service else "unavailable"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            uptime=0.0,
            version="1.0.0",
            services={}
        )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

# Analytics endpoints
@app.post("/api/v1/analytics/incidents")
async def analyze_incidents(
    request: AnalyticsRequest,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Analyze safety incidents for executive reporting"""
    REQUEST_COUNT.labels(method="POST", endpoint="/analytics/incidents").inc()
    
    with REQUEST_DURATION.time():
        try:
            result = await service.analyze_incidents(
                start_date=request.start_date,
                end_date=request.end_date,
                metrics=request.metrics,
                filters=request.filters
            )
            
            return JSONResponse(content={
                "status": "success",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Incident analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analytics/predictions")
async def generate_predictions(
    request: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service)
):
    """Generate safety predictions using machine learning models"""
    REQUEST_COUNT.labels(method="POST", endpoint="/analytics/predictions").inc()
    PREDICTION_COUNT.labels(type=request.prediction_type).inc()
    
    with REQUEST_DURATION.time():
        try:
            result = await service.generate_prediction(
                prediction_type=request.prediction_type,
                time_horizon=request.time_horizon,
                parameters=request.parameters
            )
            
            return JSONResponse(content={
                "status": "success",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analytics/reports/executive")
async def generate_executive_report(
    request: AnalyticsRequest,
    background_tasks: BackgroundTasks,
    service: ReportService = Depends(get_report_service)
):
    """Generate comprehensive executive safety report"""
    REQUEST_COUNT.labels(method="POST", endpoint="/analytics/reports/executive").inc()
    
    try:
        # Start report generation in background
        task_id = await service.generate_executive_report_async(
            start_date=request.start_date,
            end_date=request.end_date,
            filters=request.filters
        )
        
        return JSONResponse(content={
            "status": "accepted",
            "task_id": task_id,
            "message": "Executive report generation started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Executive report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/reports/{task_id}/status")
async def get_report_status(
    task_id: str,
    service: ReportService = Depends(get_report_service)
):
    """Get status of report generation task"""
    try:
        status = await service.get_report_status(task_id)
        return JSONResponse(content={
            "status": "success",
            "data": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Report status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analytics/incidents/ingest")
async def ingest_incident(
    incident: SafetyIncident,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Ingest new safety incident data"""
    REQUEST_COUNT.labels(method="POST", endpoint="/analytics/incidents/ingest").inc()
    
    try:
        result = await service.ingest_incident(incident.dict())
        
        return JSONResponse(content={
            "status": "success",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Incident ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        reload=settings.debug
    )