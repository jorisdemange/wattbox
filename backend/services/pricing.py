from datetime import datetime, time
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class PricingService:
    def __init__(self, base_price_per_kwh: float = 0.42):
        self.base_price_per_kwh = base_price_per_kwh
        
        # Time-of-use pricing (optional)
        self.time_of_use_rates: Dict[str, Dict] = {
            'peak': {
                'start': time(7, 0),
                'end': time(23, 0),
                'multiplier': 1.2
            },
            'off_peak': {
                'start': time(23, 0),
                'end': time(7, 0),
                'multiplier': 0.8
            }
        }
        
        # Tiered pricing thresholds (optional)
        self.tier_thresholds = [
            {'limit': 200, 'price': self.base_price_per_kwh * 0.9},
            {'limit': 400, 'price': self.base_price_per_kwh},
            {'limit': float('inf'), 'price': self.base_price_per_kwh * 1.3}
        ]
    
    def get_current_price(self, timestamp: Optional[datetime] = None, 
                         enable_time_of_use: bool = False) -> float:
        """Get electricity price for given timestamp"""
        if not enable_time_of_use:
            return self.base_price_per_kwh
        
        if timestamp is None:
            timestamp = datetime.now()
        
        current_time = timestamp.time()
        
        # Check time-of-use rates
        for period, config in self.time_of_use_rates.items():
            start = config['start']
            end = config['end']
            
            # Handle overnight periods
            if start > end:
                if current_time >= start or current_time < end:
                    return self.base_price_per_kwh * config['multiplier']
            else:
                if start <= current_time < end:
                    return self.base_price_per_kwh * config['multiplier']
        
        return self.base_price_per_kwh
    
    def calculate_cost(self, kwh_used: float, 
                      price_per_kwh: Optional[float] = None) -> float:
        """Calculate cost for given kWh usage"""
        if price_per_kwh is None:
            price_per_kwh = self.base_price_per_kwh
        
        return round(kwh_used * price_per_kwh, 2)
    
    def calculate_tiered_cost(self, kwh_used: float, enable_tiers: bool = False) -> float:
        """Calculate cost using tiered pricing"""
        if not enable_tiers:
            return self.calculate_cost(kwh_used)
        
        total_cost = 0.0
        remaining_kwh = kwh_used
        
        for tier in self.tier_thresholds:
            if remaining_kwh <= 0:
                break
            
            tier_usage = min(remaining_kwh, tier['limit'])
            total_cost += tier_usage * tier['price']
            remaining_kwh -= tier_usage
        
        return round(total_cost, 2)
    
    def estimate_monthly_cost(self, daily_readings: List[float]) -> Dict[str, float]:
        """Estimate monthly cost based on recent daily usage"""
        if not daily_readings:
            return {
                'estimated_monthly_kwh': 0,
                'estimated_monthly_cost': 0,
                'average_daily_kwh': 0,
                'average_daily_cost': 0
            }
        
        # Calculate average daily usage
        avg_daily_kwh = sum(daily_readings) / len(daily_readings)
        avg_daily_cost = self.calculate_cost(avg_daily_kwh)
        
        # Estimate monthly (30 days)
        estimated_monthly_kwh = avg_daily_kwh * 30
        estimated_monthly_cost = self.calculate_cost(estimated_monthly_kwh)
        
        return {
            'estimated_monthly_kwh': round(estimated_monthly_kwh, 2),
            'estimated_monthly_cost': round(estimated_monthly_cost, 2),
            'average_daily_kwh': round(avg_daily_kwh, 2),
            'average_daily_cost': round(avg_daily_cost, 2)
        }
    
    def calculate_period_cost(self, start_kwh: float, end_kwh: float, 
                            price_per_kwh: Optional[float] = None) -> Dict[str, float]:
        """Calculate cost for a period given start and end readings"""
        kwh_used = end_kwh - start_kwh
        
        if kwh_used < 0:
            logger.warning(f"Negative usage detected: {start_kwh} -> {end_kwh}")
            kwh_used = 0
        
        cost = self.calculate_cost(kwh_used, price_per_kwh)
        
        return {
            'kwh_used': round(kwh_used, 2),
            'cost': cost,
            'price_per_kwh': price_per_kwh or self.base_price_per_kwh
        }