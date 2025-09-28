import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
from models import (
    Customer, Order, Return, Refund, FraudPattern, AnalyticsMetrics, 
    CustomerRiskProfile, RiskLevel, ReturnReason, QueryFilter
)

class FraudDetectionEngine:
    """Advanced fraud detection engine for e-commerce returns"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
        # Fraud detection thresholds
        self.RETURN_RATE_THRESHOLD = 0.3  # 30% return rate is suspicious
        self.HIGH_VALUE_RETURN_THRESHOLD = 500.0  # Returns above $500
        self.FREQUENT_RETURNER_THRESHOLD = 5  # More than 5 returns in 30 days
        self.RAPID_RETURN_HOURS = 24  # Returns within 24 hours of delivery
        self.SUSPICIOUS_REASON_PATTERNS = ['changed_mind', 'not_as_described']
        
    async def calculate_fraud_score(self, customer_id: str) -> Tuple[float, List[str], RiskLevel]:
        """Calculate comprehensive fraud score for a customer"""
        
        customer_data = await self._get_customer_analytics_data(customer_id)
        if not customer_data:
            return 0.0, [], RiskLevel.LOW
            
        score = 0.0
        indicators = []
        
        # 1. Return Rate Analysis (0-30 points)
        return_rate = customer_data.get('return_rate', 0)
        if return_rate > self.RETURN_RATE_THRESHOLD:
            score += min(30, return_rate * 100)
            indicators.append(f"High return rate: {return_rate:.2%}")
            
        # 2. Return Frequency (0-25 points)
        recent_returns = customer_data.get('recent_returns_30d', 0)
        if recent_returns > self.FREQUENT_RETURNER_THRESHOLD:
            score += min(25, recent_returns * 4)
            indicators.append(f"Frequent returner: {recent_returns} returns in 30 days")
            
        # 3. Return Value Patterns (0-20 points)
        avg_return_value = customer_data.get('avg_return_value', 0)
        if avg_return_value > self.HIGH_VALUE_RETURN_THRESHOLD:
            score += min(20, (avg_return_value / self.HIGH_VALUE_RETURN_THRESHOLD) * 10)
            indicators.append(f"High-value returns: avg ${avg_return_value:.2f}")
            
        # 4. Rapid Returns (0-15 points)
        rapid_returns = customer_data.get('rapid_returns', 0)
        if rapid_returns > 0:
            score += min(15, rapid_returns * 7)
            indicators.append(f"Rapid returns: {rapid_returns} returns within 24h of delivery")
            
        # 5. Suspicious Reason Patterns (0-10 points)
        suspicious_reasons = customer_data.get('suspicious_reason_count', 0)
        if suspicious_reasons > 2:
            score += min(10, suspicious_reasons * 2)
            indicators.append(f"Suspicious return reasons: {suspicious_reasons} occurrences")
            
        # Determine risk level
        if score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif score >= 50:
            risk_level = RiskLevel.HIGH
        elif score >= 25:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
            
        return min(100.0, score), indicators, risk_level
    
    async def _get_customer_analytics_data(self, customer_id: str) -> Dict[str, Any]:
        """Get comprehensive customer analytics data"""
        
        # Get orders
        orders = await self.db.orders.find({"customer_id": customer_id}).to_list(1000)
        returns = await self.db.returns.find({"customer_id": customer_id}).to_list(1000)
        
        if not orders:
            return {}
            
        total_orders = len(orders)
        total_returns = len(returns)
        return_rate = total_returns / total_orders if total_orders > 0 else 0
        
        # Calculate recent returns (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_returns = len([r for r in returns if r['return_date'] >= thirty_days_ago])
        
        # Calculate average return value
        return_values = [r['refund_amount'] for r in returns]
        avg_return_value = sum(return_values) / len(return_values) if return_values else 0
        
        # Count rapid returns (within 24 hours of delivery)
        rapid_returns = 0
        for ret in returns:
            order = next((o for o in orders if o['id'] == ret['order_id']), None)
            if order and order.get('status') == 'delivered':
                delivery_date = order.get('updated_at', order['order_date'])
                if ret['return_date'] <= delivery_date + timedelta(hours=24):
                    rapid_returns += 1
        
        # Count suspicious reason patterns
        reason_counts = Counter([r['reason'] for r in returns])
        suspicious_reasons = sum([reason_counts[reason] for reason in self.SUSPICIOUS_REASON_PATTERNS])
        
        return {
            'total_orders': total_orders,
            'total_returns': total_returns,
            'return_rate': return_rate,
            'recent_returns_30d': recent_returns,
            'avg_return_value': avg_return_value,
            'rapid_returns': rapid_returns,
            'suspicious_reason_count': suspicious_reasons,
            'return_reasons': dict(reason_counts)
        }
    
    async def detect_anomalies(self) -> List[FraudPattern]:
        """Detect system-wide fraud patterns and anomalies"""
        
        patterns = []
        
        # Pattern 1: Mass return events
        mass_returns = await self._detect_mass_return_events()
        patterns.extend(mass_returns)
        
        # Pattern 2: Coordinated fraud rings
        fraud_rings = await self._detect_potential_fraud_rings()
        patterns.extend(fraud_rings)
        
        # Pattern 3: Product-specific return abuse
        product_abuse = await self._detect_product_return_abuse()
        patterns.extend(product_abuse)
        
        return patterns
    
    async def _detect_mass_return_events(self) -> List[FraudPattern]:
        """Detect customers with unusually high return activity in short periods"""
        
        patterns = []
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Group returns by customer in last 7 days
        pipeline = [
            {"$match": {"return_date": {"$gte": seven_days_ago}}},
            {"$group": {
                "_id": "$customer_id",
                "return_count": {"$sum": 1},
                "total_refund": {"$sum": "$refund_amount"},
                "customer_email": {"$first": "$customer_email"}
            }},
            {"$match": {"return_count": {"$gte": 3}}}  # 3+ returns in 7 days
        ]
        
        results = await self.db.returns.aggregate(pipeline).to_list(100)
        
        for result in results:
            pattern = FraudPattern(
                customer_id=result['_id'],
                pattern_type="mass_return_event",
                description=f"Customer has {result['return_count']} returns in 7 days totaling ${result['total_refund']:.2f}",
                severity=RiskLevel.HIGH,
                evidence={
                    "return_count_7d": result['return_count'],
                    "total_refund_7d": result['total_refund'],
                    "customer_email": result['customer_email']
                }
            )
            patterns.append(pattern)
            
        return patterns
    
    async def _detect_potential_fraud_rings(self) -> List[FraudPattern]:
        """Detect potential coordinated fraud through shipping address analysis"""
        
        patterns = []
        
        # Find multiple customers using same shipping address with high return rates
        pipeline = [
            {"$group": {
                "_id": "$shipping_address",
                "customers": {"$addToSet": "$customer_id"},
                "customer_emails": {"$addToSet": "$customer_email"},
                "order_count": {"$sum": 1}
            }},
            {"$match": {"$expr": {"$gte": [{"$size": "$customers"}, 3]}}}  # 3+ different customers
        ]
        
        results = await self.db.orders.aggregate(pipeline).to_list(100)
        
        for result in results:
            # Check return rates for these customers
            customer_ids = result['customers']
            return_counts = []
            
            for customer_id in customer_ids:
                customer_returns = await self.db.returns.count_documents({"customer_id": customer_id})
                customer_orders = await self.db.orders.count_documents({"customer_id": customer_id})
                return_rate = customer_returns / customer_orders if customer_orders > 0 else 0
                return_counts.append(return_rate)
            
            avg_return_rate = sum(return_counts) / len(return_counts)
            
            if avg_return_rate > 0.2:  # Average return rate > 20%
                pattern = FraudPattern(
                    customer_id=customer_ids[0],  # Primary customer
                    pattern_type="potential_fraud_ring",
                    description=f"Multiple customers ({len(customer_ids)}) using same address with {avg_return_rate:.1%} avg return rate",
                    severity=RiskLevel.CRITICAL,
                    evidence={
                        "shared_address": result['_id'],
                        "customer_count": len(customer_ids),
                        "avg_return_rate": avg_return_rate,
                        "customer_emails": result['customer_emails']
                    }
                )
                patterns.append(pattern)
                
        return patterns
    
    async def _detect_product_return_abuse(self) -> List[FraudPattern]:
        """Detect products with suspicious return patterns"""
        
        patterns = []
        
        # Group returns by product
        pipeline = [
            {"$group": {
                "_id": "$product_id",
                "return_count": {"$sum": 1},
                "product_name": {"$first": "$product_name"},
                "customers": {"$addToSet": "$customer_id"},
                "avg_refund": {"$avg": "$refund_amount"}
            }},
            {"$match": {"return_count": {"$gte": 5}}}  # Products with 5+ returns
        ]
        
        results = await self.db.returns.aggregate(pipeline).to_list(100)
        
        for result in results:
            # Calculate product return rate
            total_orders = await self.db.orders.count_documents({
                "items.product_id": result['_id']
            })
            return_rate = result['return_count'] / total_orders if total_orders > 0 else 0
            
            if return_rate > 0.4:  # Return rate > 40%
                pattern = FraudPattern(
                    customer_id="SYSTEM",
                    pattern_type="product_return_abuse",
                    description=f"Product '{result['product_name']}' has {return_rate:.1%} return rate across {len(result['customers'])} customers",
                    severity=RiskLevel.HIGH,
                    evidence={
                        "product_id": result['_id'],
                        "product_name": result['product_name'],
                        "return_rate": return_rate,
                        "return_count": result['return_count'],
                        "unique_customers": len(result['customers']),
                        "avg_refund": result['avg_refund']
                    }
                )
                patterns.append(pattern)
                
        return patterns


class AnalyticsEngine:
    """Comprehensive analytics engine for e-commerce return analysis"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.fraud_engine = FraudDetectionEngine(db)
    
    async def get_dashboard_metrics(self, filters: Optional[QueryFilter] = None) -> AnalyticsMetrics:
        """Get key metrics for the dashboard"""
        
        # Build date filter
        date_filter = {}
        if filters:
            if filters.start_date:
                date_filter["$gte"] = datetime.combine(filters.start_date, datetime.min.time())
            if filters.end_date:
                date_filter["$lte"] = datetime.combine(filters.end_date, datetime.max.time())
        
        order_filter = {"order_date": date_filter} if date_filter else {}
        return_filter = {"return_date": date_filter} if date_filter else {}
        
        # Get basic counts
        total_orders = await self.db.orders.count_documents(order_filter)
        total_returns = await self.db.returns.count_documents(return_filter)
        total_refunds = await self.db.refunds.count_documents({})
        
        # Calculate rates
        overall_return_rate = total_returns / total_orders if total_orders > 0 else 0
        
        # Get fraud detection metrics
        high_risk_customers = await self.db.customers.count_documents({"risk_level": "high"})
        fraud_suspected_returns = await self.db.returns.count_documents({"is_fraud_suspected": True})
        fraud_detection_rate = fraud_suspected_returns / total_returns if total_returns > 0 else 0
        
        # Calculate processing times
        processed_refunds = await self.db.refunds.find({"status": "processed"}).to_list(1000)
        processing_times = []
        for refund in processed_refunds:
            if refund.get('processing_time_days'):
                processing_times.append(refund['processing_time_days'])
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Calculate revenue metrics
        orders = await self.db.orders.find(order_filter).to_list(10000)
        total_revenue = sum([order['total_amount'] for order in orders])
        
        refunds = await self.db.refunds.find({}).to_list(10000)
        total_refund_amount = sum([refund['amount'] for refund in refunds])
        
        # Top return reasons
        return_reasons_pipeline = [
            {"$group": {"_id": "$reason", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        reason_results = await self.db.returns.aggregate(return_reasons_pipeline).to_list(5)
        top_return_reasons = {result['_id']: result['count'] for result in reason_results}
        
        # Date range
        date_range = {}
        if filters and filters.start_date and filters.end_date:
            date_range = {
                "start_date": filters.start_date.isoformat(),
                "end_date": filters.end_date.isoformat()
            }
        
        return AnalyticsMetrics(
            total_orders=total_orders,
            total_returns=total_returns,
            total_refunds=total_refunds,
            overall_return_rate=overall_return_rate,
            fraud_detection_rate=fraud_detection_rate,
            avg_processing_time=avg_processing_time,
            total_revenue=total_revenue,
            total_refund_amount=total_refund_amount,
            high_risk_customers=high_risk_customers,
            top_return_reasons=top_return_reasons,
            date_range=date_range
        )
    
    async def get_customer_risk_profiles(self, limit: int = 100) -> List[CustomerRiskProfile]:
        """Get customer risk profiles for fraud analysis"""
        
        customers = await self.db.customers.find().limit(limit).to_list(limit)
        profiles = []
        
        for customer in customers:
            # Get customer analytics data
            customer_data = await self.fraud_engine._get_customer_analytics_data(customer['id'])
            
            # Calculate risk metrics
            fraud_score, indicators, risk_level = await self.fraud_engine.calculate_fraud_score(customer['id'])
            
            # Generate recommendation
            recommendation = self._generate_customer_recommendation(risk_level, indicators)
            
            profile = CustomerRiskProfile(
                customer_id=customer['id'],
                email=customer['email'],
                risk_score=fraud_score,
                risk_level=risk_level,
                return_frequency=customer_data.get('recent_returns_30d', 0),
                avg_order_value=customer_data.get('avg_return_value', 0),
                return_value_ratio=customer_data.get('return_rate', 0),
                suspicious_patterns=indicators,
                recommendation=recommendation
            )
            profiles.append(profile)
        
        return sorted(profiles, key=lambda x: x.risk_score, reverse=True)
    
    def _generate_customer_recommendation(self, risk_level: RiskLevel, indicators: List[str]) -> str:
        """Generate actionable recommendations based on risk assessment"""
        
        if risk_level == RiskLevel.CRITICAL:
            return "IMMEDIATE ACTION: Suspend account and investigate. Consider fraud team review."
        elif risk_level == RiskLevel.HIGH:
            return "Monitor closely. Require additional verification for returns."
        elif risk_level == RiskLevel.MEDIUM:
            return "Flag for review. Consider return policy restrictions."
        else:
            return "Low risk. Continue normal processing."
    
    async def get_trend_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Get trend analysis for returns and fraud over time"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Daily return trends
        pipeline = [
            {"$match": {"return_date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$return_date"}},
                "return_count": {"$sum": 1},
                "fraud_count": {"$sum": {"$cond": ["$is_fraud_suspected", 1, 0]}},
                "total_refund": {"$sum": "$refund_amount"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        daily_trends = await self.db.returns.aggregate(pipeline).to_list(days)
        
        # Calculate trend indicators
        return_counts = [day['return_count'] for day in daily_trends]
        fraud_counts = [day['fraud_count'] for day in daily_trends]
        
        return_trend = "increasing" if len(return_counts) > 1 and return_counts[-1] > return_counts[0] else "stable"
        fraud_trend = "increasing" if len(fraud_counts) > 1 and fraud_counts[-1] > fraud_counts[0] else "stable"
        
        return {
            "daily_trends": daily_trends,
            "return_trend": return_trend,
            "fraud_trend": fraud_trend,
            "avg_daily_returns": sum(return_counts) / len(return_counts) if return_counts else 0,
            "avg_daily_fraud": sum(fraud_counts) / len(fraud_counts) if fraud_counts else 0
        }