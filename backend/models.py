from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class ReturnReason(str, Enum):
    DEFECTIVE = "defective"
    SIZE_ISSUE = "size_issue"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    LATE_DELIVERY = "late_delivery"
    DAMAGED_SHIPPING = "damaged_shipping"
    DUPLICATE_ORDER = "duplicate_order"

class RefundStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSED = "processed"
    REJECTED = "rejected"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Customer Model
class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    total_orders: int = 0
    total_returns: int = 0
    return_rate: float = 0.0
    fraud_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    is_blacklisted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CustomerCreate(BaseModel):
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

# Product Model
class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    sub_category: Optional[str] = None
    price: float
    cost: float
    margin: float
    seller_id: str
    return_rate: float = 0.0
    fraud_return_rate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    category: str
    sub_category: Optional[str] = None
    price: float
    cost: float
    seller_id: str

# Seller Model
class Seller(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    rating: float = 5.0
    total_sales: float = 0.0
    return_rate: float = 0.0
    fraud_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SellerCreate(BaseModel):
    name: str
    email: str
    rating: Optional[float] = 5.0

# Order Model
class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    customer_email: str
    items: List[OrderItem]
    total_amount: float
    order_date: datetime = Field(default_factory=datetime.utcnow)
    status: OrderStatus = OrderStatus.PENDING
    shipping_address: str
    payment_method: str
    is_returned: bool = False
    return_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderCreate(BaseModel):
    customer_id: str
    items: List[OrderItem]
    shipping_address: str
    payment_method: str

# Return Model
class Return(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    customer_id: str
    customer_email: str
    product_id: str
    product_name: str
    quantity_returned: int
    reason: ReturnReason
    description: Optional[str] = None
    return_date: datetime = Field(default_factory=datetime.utcnow)
    refund_amount: float
    is_fraud_suspected: bool = False
    fraud_score: float = 0.0
    fraud_indicators: List[str] = []
    processing_time_days: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReturnCreate(BaseModel):
    order_id: str
    product_id: str
    quantity_returned: int
    reason: ReturnReason
    description: Optional[str] = None

# Refund Model
class Refund(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    return_id: str
    order_id: str
    customer_id: str
    amount: float
    status: RefundStatus = RefundStatus.PENDING
    requested_date: datetime = Field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = None
    processing_time_days: Optional[int] = None
    refund_method: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RefundCreate(BaseModel):
    return_id: str
    refund_method: str

# Analytics Models
class FraudPattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    pattern_type: str
    description: str
    severity: RiskLevel
    detected_date: datetime = Field(default_factory=datetime.utcnow)
    evidence: Dict[str, Any] = {}

class AnalyticsMetrics(BaseModel):
    total_orders: int
    total_returns: int
    total_refunds: int
    overall_return_rate: float
    fraud_detection_rate: float
    avg_processing_time: float
    total_revenue: float
    total_refund_amount: float
    high_risk_customers: int
    top_return_reasons: Dict[str, int]
    date_range: Dict[str, str]

class CustomerRiskProfile(BaseModel):
    customer_id: str
    email: str
    risk_score: float
    risk_level: RiskLevel
    return_frequency: int
    avg_order_value: float
    return_value_ratio: float
    suspicious_patterns: List[str]
    recommendation: str

# Query and Export Models
class QueryFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    customer_ids: Optional[List[str]] = None
    product_categories: Optional[List[str]] = None
    return_reasons: Optional[List[str]] = None
    fraud_risk_levels: Optional[List[str]] = None
    min_order_value: Optional[float] = None
    max_order_value: Optional[float] = None

class ExportRequest(BaseModel):
    export_type: str  # 'csv', 'json', 'excel'
    data_type: str   # 'orders', 'returns', 'customers', 'analytics'
    filters: Optional[QueryFilter] = None
    include_fraud_scores: bool = True

class ExportResponse(BaseModel):
    file_url: str
    file_name: str
    export_type: str
    record_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)