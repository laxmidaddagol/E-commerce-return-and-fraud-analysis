from fastapi import FastAPI, APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date, timedelta
import csv
import json
import io
import pandas as pd

# Import our models and engines
from models import (
    Customer, Product, Seller, Order, Return, Refund,
    CustomerCreate, ProductCreate, SellerCreate, OrderCreate, ReturnCreate, RefundCreate,
    AnalyticsMetrics, CustomerRiskProfile, FraudPattern, QueryFilter, ExportRequest, ExportResponse,
    OrderStatus, ReturnReason, RefundStatus, RiskLevel
)
from analytics import AnalyticsEngine, FraudDetectionEngine
from data_generator import ECommerceDataGenerator

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize engines
analytics_engine = AnalyticsEngine(db)
fraud_engine = FraudDetectionEngine(db)
data_generator = ECommerceDataGenerator(db)

# Create the main app without a prefix
app = FastAPI(title="E-Commerce Return & Fraud Analysis API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Legacy status check endpoints (keeping for compatibility)
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

@api_router.get("/")
async def root():
    return {
        "message": "E-Commerce Return & Fraud Analysis API", 
        "version": "1.0.0",
        "description": "Comprehensive analytics pipeline for e-commerce return data and fraud detection"
    }

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# ====================
# DATA MANAGEMENT ENDPOINTS
# ====================

@api_router.post("/generate-sample-data")
async def generate_sample_data(
    customers: int = Query(1000, ge=100, le=10000),
    sellers: int = Query(50, ge=10, le=500),
    products: int = Query(500, ge=50, le=5000),
    orders: int = Query(5000, ge=500, le=50000),
    return_rate: float = Query(0.15, ge=0.05, le=0.5)
):
    """Generate comprehensive sample e-commerce data for analysis"""
    try:
        result = await data_generator.generate_sample_data(
            customers=customers,
            sellers=sellers,
            products=products,
            orders=orders,
            return_rate=return_rate
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data generation failed: {str(e)}")

@api_router.get("/data-status")
async def get_data_status():
    """Get current data status and counts"""
    try:
        counts = {}
        collections = ['customers', 'sellers', 'products', 'orders', 'returns', 'refunds']
        
        for collection in collections:
            count = await db[collection].count_documents({})
            counts[collection] = count
        
        return {"success": True, "data_counts": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data status: {str(e)}")

# ====================
# ANALYTICS ENDPOINTS
# ====================

@api_router.get("/analytics/dashboard", response_model=AnalyticsMetrics)
async def get_dashboard_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    customer_ids: Optional[str] = Query(None),
    product_categories: Optional[str] = Query(None)
):
    """Get comprehensive dashboard metrics"""
    try:
        # Parse filters
        filters = QueryFilter()
        if start_date:
            filters.start_date = start_date
        if end_date:
            filters.end_date = end_date
        if customer_ids:
            filters.customer_ids = customer_ids.split(',')
        if product_categories:
            filters.product_categories = product_categories.split(',')
        
        metrics = await analytics_engine.get_dashboard_metrics(filters)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard metrics: {str(e)}")

@api_router.get("/analytics/customer-risk-profiles", response_model=List[CustomerRiskProfile])
async def get_customer_risk_profiles(limit: int = Query(100, ge=10, le=1000)):
    """Get customer risk profiles for fraud analysis"""
    try:
        profiles = await analytics_engine.get_customer_risk_profiles(limit)
        return profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get customer risk profiles: {str(e)}")

@api_router.get("/analytics/trends")
async def get_trend_analysis(days: int = Query(30, ge=7, le=365)):
    """Get trend analysis for returns and fraud over time"""
    try:
        trends = await analytics_engine.get_trend_analysis(days)
        return {"success": True, "data": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trend analysis: {str(e)}")

# ====================
# FRAUD DETECTION ENDPOINTS
# ====================

@api_router.get("/fraud/customer-score/{customer_id}")
async def get_customer_fraud_score(customer_id: str):
    """Calculate fraud score for a specific customer"""
    try:
        score, indicators, risk_level = await fraud_engine.calculate_fraud_score(customer_id)
        
        return {
            "customer_id": customer_id,
            "fraud_score": score,
            "risk_level": risk_level,
            "fraud_indicators": indicators,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate fraud score: {str(e)}")

@api_router.get("/fraud/patterns", response_model=List[FraudPattern])
async def detect_fraud_patterns():
    """Detect system-wide fraud patterns and anomalies"""
    try:
        patterns = await fraud_engine.detect_anomalies()
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect fraud patterns: {str(e)}")

# ====================
# DATA QUERY ENDPOINTS
# ====================

@api_router.get("/data/customers", response_model=List[Customer])
async def get_customers(
    limit: int = Query(100, ge=10, le=1000),
    risk_level: Optional[str] = Query(None),
    min_return_rate: Optional[float] = Query(None)
):
    """Get customers with optional filtering"""
    try:
        filter_query = {}
        if risk_level:
            filter_query["risk_level"] = risk_level
        if min_return_rate is not None:
            filter_query["return_rate"] = {"$gte": min_return_rate}
        
        customers = await db.customers.find(filter_query).limit(limit).to_list(limit)
        return [Customer(**customer) for customer in customers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get customers: {str(e)}")

@api_router.get("/data/returns", response_model=List[Return])
async def get_returns(
    limit: int = Query(100, ge=10, le=1000),
    fraud_suspected: Optional[bool] = Query(None),
    return_reason: Optional[str] = Query(None)
):
    """Get returns with optional filtering"""
    try:
        filter_query = {}
        if fraud_suspected is not None:
            filter_query["is_fraud_suspected"] = fraud_suspected
        if return_reason:
            filter_query["reason"] = return_reason
        
        returns = await db.returns.find(filter_query).limit(limit).to_list(limit)
        return [Return(**return_data) for return_data in returns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get returns: {str(e)}")

@api_router.get("/data/orders", response_model=List[Order])
async def get_orders(
    limit: int = Query(100, ge=10, le=1000),
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get orders with optional filtering"""
    try:
        filter_query = {}
        if customer_id:
            filter_query["customer_id"] = customer_id
        if status:
            filter_query["status"] = status
        
        orders = await db.orders.find(filter_query).limit(limit).to_list(limit)
        return [Order(**order) for order in orders]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")

# ====================
# EXPORT ENDPOINTS (Power BI / Tableau)
# ====================

@api_router.post("/export/csv")
async def export_to_csv(request: ExportRequest):
    """Export data to CSV format for Power BI/Tableau"""
    try:
        # Get data based on type
        data = await _get_export_data(request.data_type, request.filters)
        
        # Convert to CSV
        output = io.StringIO()
        if data:
            df = pd.DataFrame(data)
            df.to_csv(output, index=False)
            output.seek(0)
            
            # Create response
            filename = f"{request.data_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(status_code=404, detail="No data found for export")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@api_router.post("/export/json")
async def export_to_json(request: ExportRequest):
    """Export data to JSON format"""
    try:
        # Get data based on type
        data = await _get_export_data(request.data_type, request.filters)
        
        if data:
            filename = f"{request.data_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            return StreamingResponse(
                io.BytesIO(json.dumps(data, default=str).encode('utf-8')),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(status_code=404, detail="No data found for export")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

async def _get_export_data(data_type: str, filters: Optional[QueryFilter]) -> List[Dict]:
    """Get data for export based on type and filters"""
    
    # Build MongoDB filter
    mongo_filter = {}
    if filters:
        if filters.start_date:
            date_field = "order_date" if data_type == "orders" else "return_date" if data_type == "returns" else "created_at"
            mongo_filter[date_field] = {"$gte": datetime.combine(filters.start_date, datetime.min.time())}
        if filters.end_date:
            date_field = "order_date" if data_type == "orders" else "return_date" if data_type == "returns" else "created_at"
            if date_field in mongo_filter:
                mongo_filter[date_field]["$lte"] = datetime.combine(filters.end_date, datetime.max.time())
            else:
                mongo_filter[date_field] = {"$lte": datetime.combine(filters.end_date, datetime.max.time())}
    
    # Get data from appropriate collection
    if data_type == "customers":
        collection = db.customers
    elif data_type == "orders":
        collection = db.orders
    elif data_type == "returns":
        collection = db.returns
    elif data_type == "refunds":
        collection = db.refunds
    elif data_type == "analytics":
        # For analytics, return dashboard metrics
        metrics = await analytics_engine.get_dashboard_metrics(filters)
        return [metrics.dict()]
    else:
        raise ValueError(f"Unknown data type: {data_type}")
    
    # Fetch data
    data = await collection.find(mongo_filter).limit(10000).to_list(10000)
    
    # Remove MongoDB _id field and convert dates to strings
    for item in data:
        if '_id' in item:
            del item['_id']
        # Convert datetime objects to strings for JSON serialization
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.isoformat()
    
    return data

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
