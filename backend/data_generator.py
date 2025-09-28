import random
import string
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import (
    Customer, Product, Seller, Order, OrderItem, Return, Refund,
    OrderStatus, ReturnReason, RefundStatus, RiskLevel
)

fake = Faker()

class ECommerceDataGenerator:
    """Generate realistic e-commerce data for demonstration purposes"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
        # Product categories and subcategories
        self.categories = {
            "Electronics": ["Smartphones", "Laptops", "Tablets", "Accessories", "Gaming"],
            "Clothing": ["Men's Fashion", "Women's Fashion", "Kids Fashion", "Shoes", "Accessories"],
            "Home & Garden": ["Furniture", "Kitchen", "Bedding", "Outdoor", "Tools"],
            "Sports": ["Fitness", "Outdoor Sports", "Team Sports", "Water Sports", "Winter Sports"],
            "Beauty": ["Skincare", "Makeup", "Hair Care", "Fragrance", "Personal Care"]
        }
        
        # Return reasons with fraud likelihood weights
        self.return_reasons_weights = {
            ReturnReason.DEFECTIVE: 0.15,
            ReturnReason.SIZE_ISSUE: 0.25,
            ReturnReason.NOT_AS_DESCRIBED: 0.20,
            ReturnReason.CHANGED_MIND: 0.15,
            ReturnReason.LATE_DELIVERY: 0.10,
            ReturnReason.DAMAGED_SHIPPING: 0.10,
            ReturnReason.DUPLICATE_ORDER: 0.05
        }
        
        # Fraud probability by return reason
        self.fraud_probability = {
            ReturnReason.CHANGED_MIND: 0.4,
            ReturnReason.NOT_AS_DESCRIBED: 0.3,
            ReturnReason.DEFECTIVE: 0.1,
            ReturnReason.SIZE_ISSUE: 0.05,
            ReturnReason.LATE_DELIVERY: 0.02,
            ReturnReason.DAMAGED_SHIPPING: 0.02,
            ReturnReason.DUPLICATE_ORDER: 0.01
        }
    
    async def generate_sample_data(self, 
                                 customers: int = 1000,
                                 sellers: int = 50,
                                 products: int = 500,
                                 orders: int = 5000,
                                 return_rate: float = 0.15) -> Dict[str, int]:
        """Generate comprehensive sample e-commerce data"""
        
        print("Starting data generation...")
        
        # Clear existing data
        await self._clear_existing_data()
        
        # Generate base data
        generated_sellers = await self._generate_sellers(sellers)
        generated_products = await self._generate_products(products, generated_sellers)
        generated_customers = await self._generate_customers(customers)
        generated_orders = await self._generate_orders(orders, generated_customers, generated_products)
        
        # Generate returns and refunds
        returns_count = int(orders * return_rate)
        generated_returns = await self._generate_returns(returns_count, generated_orders)
        generated_refunds = await self._generate_refunds(generated_returns)
        
        # Update customer analytics
        await self._update_customer_analytics()
        
        print("Data generation completed!")
        
        return {
            "customers": len(generated_customers),
            "sellers": len(generated_sellers),
            "products": len(generated_products),
            "orders": len(generated_orders),
            "returns": len(generated_returns),
            "refunds": len(generated_refunds)
        }
    
    async def _clear_existing_data(self):
        """Clear existing demo data"""
        collections = ['customers', 'sellers', 'products', 'orders', 'returns', 'refunds', 'fraud_patterns']
        for collection in collections:
            await self.db[collection].delete_many({})
    
    async def _generate_sellers(self, count: int) -> List[Dict]:
        """Generate seller data"""
        sellers = []
        
        for _ in range(count):
            seller = Seller(
                name=fake.company(),
                email=fake.company_email(),
                rating=round(random.uniform(3.5, 5.0), 1)
            )
            sellers.append(seller.dict())
        
        if sellers:
            await self.db.sellers.insert_many(sellers)
        return sellers
    
    async def _generate_products(self, count: int, sellers: List[Dict]) -> List[Dict]:
        """Generate product data"""
        products = []
        
        for _ in range(count):
            category = random.choice(list(self.categories.keys()))
            subcategory = random.choice(self.categories[category])
            
            # Price based on category
            if category == "Electronics":
                price = round(random.uniform(50, 2000), 2)
            elif category == "Clothing":
                price = round(random.uniform(15, 300), 2)
            else:
                price = round(random.uniform(10, 500), 2)
            
            cost = round(price * random.uniform(0.3, 0.7), 2)
            margin = round(((price - cost) / price) * 100, 2)
            
            product = Product(
                name=f"{fake.catch_phrase()} {subcategory}",
                category=category,
                sub_category=subcategory,
                price=price,
                cost=cost,
                margin=margin,
                seller_id=random.choice(sellers)['id']
            )
            products.append(product.dict())
        
        if products:
            await self.db.products.insert_many(products)
        return products
    
    async def _generate_customers(self, count: int) -> List[Dict]:
        """Generate customer data with varied risk profiles"""
        customers = []
        
        for i in range(count):
            # Create different customer personas
            if i < count * 0.05:  # 5% high-risk customers
                risk_profile = "high_risk"
            elif i < count * 0.15:  # 10% medium-risk customers
                risk_profile = "medium_risk"
            else:  # 85% low-risk customers
                risk_profile = "low_risk"
            
            customer = Customer(
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone=fake.phone_number(),
                registration_date=fake.date_time_between(start_date='-2y', end_date='now')
            )
            
            # Add risk profile as metadata (will be used in order generation)
            customer_dict = customer.dict()
            customer_dict['_risk_profile'] = risk_profile
            customers.append(customer_dict)
        
        if customers:
            await self.db.customers.insert_many(customers)
        return customers
    
    async def _generate_orders(self, count: int, customers: List[Dict], products: List[Dict]) -> List[Dict]:
        """Generate order data"""
        orders = []
        
        for _ in range(count):
            customer = random.choice(customers)
            
            # Number of items based on customer risk profile
            risk_profile = customer.get('_risk_profile', 'low_risk')
            if risk_profile == 'high_risk':
                num_items = random.randint(1, 3)
                order_multiplier = random.uniform(1.2, 2.0)  # Higher value orders
            else:
                num_items = random.randint(1, 4)
                order_multiplier = random.uniform(0.8, 1.2)
            
            # Select random products
            order_products = random.sample(products, min(num_items, len(products)))
            
            items = []
            total_amount = 0
            
            for product in order_products:
                quantity = random.randint(1, 2)
                unit_price = product['price'] * order_multiplier
                total_price = unit_price * quantity
                
                item = OrderItem(
                    product_id=product['id'],
                    product_name=product['name'],
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                items.append(item)
                total_amount += total_price
            
            # Order date in the last 6 months
            order_date = fake.date_time_between(start_date='-6M', end_date='now')
            
            order = Order(
                customer_id=customer['id'],
                customer_email=customer['email'],
                items=items,
                total_amount=round(total_amount, 2),
                order_date=order_date,
                status=random.choice([OrderStatus.DELIVERED, OrderStatus.SHIPPED]),
                shipping_address=fake.address(),
                payment_method=random.choice(['Credit Card', 'Debit Card', 'PayPal', 'Apple Pay'])
            )
            
            orders.append(order.dict())
        
        if orders:
            await self.db.orders.insert_many(orders)
        return orders
    
    async def _generate_returns(self, count: int, orders: List[Dict]) -> List[Dict]:
        """Generate return data with realistic fraud patterns"""
        returns = []
        
        # Select orders for returns (only delivered orders)
        eligible_orders = [o for o in orders if o['status'] == OrderStatus.DELIVERED]
        selected_orders = random.sample(eligible_orders, min(count, len(eligible_orders)))
        
        for order in selected_orders:
            # Get customer risk profile
            customer = await self.db.customers.find_one({"id": order['customer_id']})
            risk_profile = customer.get('_risk_profile', 'low_risk') if customer else 'low_risk'
            
            # Select return reason based on risk profile
            if risk_profile == 'high_risk':
                # High-risk customers more likely to use suspicious reasons
                reason_weights = {
                    ReturnReason.CHANGED_MIND: 0.4,
                    ReturnReason.NOT_AS_DESCRIBED: 0.3,
                    ReturnReason.SIZE_ISSUE: 0.15,
                    ReturnReason.DEFECTIVE: 0.15
                }
            else:
                reason_weights = self.return_reasons_weights
            
            reason = random.choices(
                list(reason_weights.keys()),
                weights=list(reason_weights.values())
            )[0]
            
            # Select item to return
            item = random.choice(order['items'])
            quantity_returned = random.randint(1, item['quantity'])
            refund_amount = round(item['unit_price'] * quantity_returned * 0.95, 2)  # 5% restocking fee
            
            # Return date after order date
            return_date = order['order_date'] + timedelta(days=random.randint(1, 30))
            
            # Determine if fraud is suspected
            fraud_probability = self.fraud_probability.get(reason, 0.05)
            if risk_profile == 'high_risk':
                fraud_probability *= 3  # 3x more likely for high-risk customers
            
            is_fraud_suspected = random.random() < fraud_probability
            fraud_score = 0
            fraud_indicators = []
            
            if is_fraud_suspected:
                fraud_score = random.uniform(70, 95)
                fraud_indicators = [
                    f"Suspicious return reason: {reason}",
                    "Pattern matches known fraud indicators"
                ]
            
            # Processing time (fraud cases take longer)
            processing_days = random.randint(1, 14) if not is_fraud_suspected else random.randint(7, 21)
            
            return_obj = Return(
                order_id=order['id'],
                customer_id=order['customer_id'],
                customer_email=order['customer_email'],
                product_id=item['product_id'],
                product_name=item['product_name'],
                quantity_returned=quantity_returned,
                reason=reason,
                description=fake.text(max_nb_chars=200),
                return_date=return_date,
                refund_amount=refund_amount,
                is_fraud_suspected=is_fraud_suspected,
                fraud_score=fraud_score,
                fraud_indicators=fraud_indicators,
                processing_time_days=processing_days
            )
            
            returns.append(return_obj.dict())
        
        if returns:
            await self.db.returns.insert_many(returns)
        return returns
    
    async def _generate_refunds(self, returns: List[Dict]) -> List[Dict]:
        """Generate refund data"""
        refunds = []
        
        for return_data in returns:
            # Most returns get refunds, but fraud cases might be rejected
            if return_data['is_fraud_suspected'] and random.random() < 0.3:
                status = RefundStatus.REJECTED
                processed_date = None
                processing_time = None
            else:
                status = random.choice([RefundStatus.PROCESSED, RefundStatus.APPROVED])
                processed_date = return_data['return_date'] + timedelta(days=return_data['processing_time_days'])
                processing_time = return_data['processing_time_days']
            
            refund = Refund(
                return_id=return_data['id'],
                order_id=return_data['order_id'],
                customer_id=return_data['customer_id'],
                amount=return_data['refund_amount'],
                status=status,
                requested_date=return_data['return_date'],
                processed_date=processed_date,
                processing_time_days=processing_time,
                refund_method=random.choice(['Original Payment Method', 'Store Credit', 'Bank Transfer'])
            )
            
            refunds.append(refund.dict())
        
        if refunds:
            await self.db.refunds.insert_many(refunds)
        return refunds
    
    async def _update_customer_analytics(self):
        """Update customer analytics and risk scores"""
        
        # Update customer return rates and totals
        pipeline = [
            {"$group": {
                "_id": "$customer_id",
                "total_orders": {"$sum": 1},
                "total_amount": {"$sum": "$total_amount"}
            }}
        ]
        
        order_stats = await self.db.orders.aggregate(pipeline).to_list(10000)
        order_stats_dict = {stat['_id']: stat for stat in order_stats}
        
        # Get return stats
        return_pipeline = [
            {"$group": {
                "_id": "$customer_id",
                "total_returns": {"$sum": 1},
                "total_refunds": {"$sum": "$refund_amount"},
                "fraud_returns": {"$sum": {"$cond": ["$is_fraud_suspected", 1, 0]}}
            }}
        ]
        
        return_stats = await self.db.returns.aggregate(return_pipeline).to_list(10000)
        return_stats_dict = {stat['_id']: stat for stat in return_stats}
        
        # Update each customer
        customers = await self.db.customers.find().to_list(10000)
        
        for customer in customers:
            customer_id = customer['id']
            
            order_data = order_stats_dict.get(customer_id, {'total_orders': 0, 'total_amount': 0})
            return_data = return_stats_dict.get(customer_id, {'total_returns': 0, 'fraud_returns': 0})
            
            total_orders = order_data['total_orders']
            total_returns = return_data['total_returns']
            return_rate = total_returns / total_orders if total_orders > 0 else 0
            
            # Calculate fraud score
            fraud_score = 0
            risk_level = RiskLevel.LOW
            
            if return_rate > 0.3:
                fraud_score = min(100, return_rate * 200)
                if fraud_score >= 70:
                    risk_level = RiskLevel.CRITICAL
                elif fraud_score >= 50:
                    risk_level = RiskLevel.HIGH
                elif fraud_score >= 25:
                    risk_level = RiskLevel.MEDIUM
            
            # Update customer record
            await self.db.customers.update_one(
                {"id": customer_id},
                {"$set": {
                    "total_orders": total_orders,
                    "total_returns": total_returns,
                    "return_rate": return_rate,
                    "fraud_score": fraud_score,
                    "risk_level": risk_level
                }}
            )