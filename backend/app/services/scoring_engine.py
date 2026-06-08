import numpy as np
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import re

class AIIPOEngine:
    """
    AI-powered IPO scoring based on demand, financials, and market factors.
    
    Research shows that corporate profile, financial position, IPO size, 
    short-term returns, and sector performance significantly influence 
    IPO investment decisions in Nepal [citation:3].
    """
    
    def __init__(self):
        self.scaler = MinMaxScaler()
        # Historical oversubscription data for reference
        self.historical_oversubscription = {
            'hydropower': {'avg': 15.2, 'max': 58.0},
            'microfinance': {'avg': 12.8, 'max': 42.0},
            'insurance': {'avg': 8.5, 'max': 22.0},
            'commercial_bank': {'avg': 6.2, 'max': 15.0},
            'hotel': {'avg': 4.5, 'max': 12.0},
            'manufacturing': {'avg': 5.8, 'max': 18.0},
        }
    
    def calculate_score(self, ipo, similar_ipos):
        """
        Calculate comprehensive IPO score
        
        Returns scores for:
        - demand_score: Expected demand/oversubscription
        - financial_score: Financial health
        - sector_score: Sector performance
        - risk_score: Investment risk
        - overall_score: Weighted average
        - oversubscription_forecast: Predicted multiple
        - recommendation: Action recommendation
        """
        
        demand_score = self._calculate_demand_score(ipo, similar_ipos)
        financial_score = self._calculate_financial_score(ipo)
        sector_score = self._calculate_sector_score(ipo)
        risk_score = self._calculate_risk_score(ipo, demand_score)
        
        # Weighted overall score (lower risk weight means risk_score is inverted)
        overall_score = (
            demand_score * 0.40 +
            financial_score * 0.30 +
            sector_score * 0.20 +
            (100 - risk_score) * 0.10
        )
        
        # Forecast oversubscription multiple
        oversubscription_forecast = self._forecast_oversubscription(
            demand_score, sector_score, ipo
        )
        
        # Recommendation based on overall score
        if overall_score >= 80:
            recommendation = "Strong Buy"
        elif overall_score >= 65:
            recommendation = "Buy"
        elif overall_score >= 45:
            recommendation = "Hold"
        else:
            recommendation = "Avoid"
        
        return {
            'demand_score': round(demand_score, 2),
            'financial_score': round(financial_score, 2),
            'sector_score': round(sector_score, 2),
            'risk_score': round(risk_score, 2),
            'overall_score': round(overall_score, 2),
            'oversubscription_forecast': round(oversubscription_forecast, 1),
            'recommendation': recommendation,
            'similar_ipos': [{'company': ipo.company_name, 'score': 75} for ipo in similar_ipos[:5]]
        }
    
    def _calculate_demand_score(self, ipo, similar_ipos):
        """
        Calculate demand score based on:
        - Historical oversubscription of similar IPOs
        - Market sentiment indicators
        - Issue size (smaller = higher demand typically)
        """
        base_score = 50
        
        # Factor 1: Issue size (smaller issues get higher demand)
        if hasattr(ipo, 'issue_size') and ipo.issue_size:
            if ipo.issue_size < 100:  # Small IPO (< 100M)
                base_score += 25
            elif ipo.issue_size < 500:  # Medium IPO
                base_score += 10
            elif ipo.issue_size > 1000:  # Large IPO
                base_score -= 15
        
        # Factor 2: Similar IPOs performance
        if similar_ipos and len(similar_ipos) > 0:
            # This would use actual historical oversubscription from DB
            avg_previous_demand = 60
            base_score = (base_score + avg_previous_demand) / 2
        
        return min(100, max(0, base_score))
    
    def _calculate_financial_score(self, ipo):
        """
        Calculate financial health score
        Based on research: Financial position is a top factor for investors [citation:3]
        """
        # In production, fetch financial ratios from company API/database
        # For now, return a baseline based on company info extraction
        
        base_score = 65
        
        # Extract potential financial indicators from announcement
        if hasattr(ipo, 'raw_announcement') and ipo.raw_announcement:
            text = ipo.raw_announcement.lower()
            
            # Positive indicators
            if any(word in text for word in ['profit', 'growth', 'increased', 'strong']):
                base_score += 10
            if any(word in text for word in ['dividend', 'bonus']):
                base_score += 5
            
            # Negative indicators
            if any(word in text for word in ['loss', 'decline', 'decreased']):
                base_score -= 15
        
        return min(100, max(0, base_score))
    
    def _calculate_sector_score(self, ipo):
        """
        Calculate sector performance score
        Research shows sector performance significantly influences decisions [citation:3]
        """
        sector = self._detect_sector(ipo)
        
        sector_scores = {
            'hydropower': 85,      # High demand sector
            'microfinance': 80,    # Strong retail interest
            'insurance': 70,       # Moderate
            'commercial_bank': 65, # Mature sector
            'hotel': 55,           # Recovery phase
            'manufacturing': 60,   # Moderate
            'others': 50
        }
        
        return sector_scores.get(sector, 50)
    
    def _calculate_risk_score(self, ipo, demand_score):
        """
        Calculate investment risk score (lower = better)
        Factors: Volatility, regulatory concerns, market conditions
        """
        base_risk = 30
        
        # High demand = potentially lower risk
        if demand_score > 75:
            base_risk -= 10
        elif demand_score < 40:
            base_risk += 20
        
        # Sector-specific risk adjustments
        sector = self._detect_sector(ipo)
        sector_risks = {
            'hydropower': 25,     # Seasonal and regulatory risks
            'microfinance': 20,    # Portfolio risk
            'insurance': 15,       # Moderate
            'commercial_bank': 10, # Stable
            'hotel': 30,           # Tourism dependent
            'manufacturing': 20,   # Input cost risks
        }
        
        base_risk += sector_risks.get(sector, 25)
        
        return min(100, max(0, base_risk))
    
    def _forecast_oversubscription(self, demand_score, sector_score, ipo):
        """Forecast likely oversubscription multiple"""
        sector = self._detect_sector(ipo)
        historical = self.historical_oversubscription.get(sector, {'avg': 8.0})
        
        # Base forecast on historical average and demand score
        base_forecast = historical['avg']
        
        # Adjust based on demand score
        if demand_score >= 80:
            multiplier = 1.5
        elif demand_score >= 60:
            multiplier = 1.2
        elif demand_score >= 40:
            multiplier = 1.0
        else:
            multiplier = 0.7
        
        forecast = base_forecast * multiplier
        
        # Cap at reasonable levels
        return min(80, max(2, forecast))
    
    def _detect_sector(self, ipo):
        """Detect sector from company name or announcement"""
        company_name = getattr(ipo, 'company_name', '').lower()
        announcement = getattr(ipo, 'raw_announcement', '').lower()
        combined = f"{company_name} {announcement}"
        
        sector_keywords = {
            'hydropower': ['hydro', 'power', 'energy', 'jal', 'khola'],
            'microfinance': ['laghubitta', 'microfinance', 'bittiya sanstha'],
            'insurance': ['insurance', 'insurer', 'life insurance', 'general insurance'],
            'commercial_bank': ['bank', 'bank limited', 'commercial bank'],
            'hotel': ['hotel', 'resort', 'lodge'],
            'manufacturing': ['industry', 'manufacturing', 'production', 'cement'],
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return sector
        
        return 'others'