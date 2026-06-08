from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class IPOAnnouncement(Base):
    __tablename__ = "ipo_announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    company_symbol = Column(String(20))
    announcement_date = Column(DateTime, nullable=False)
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    issue_size = Column(Float)  # In million NPR
    units = Column(Integer)  # Number of units
    price_per_unit = Column(Float)
    issue_manager = Column(String(200))
    source = Column(String(50))  # merolagani, sharesansar, sebon
    raw_announcement = Column(Text)
    status = Column(String(50))  # upcoming, open, closed, approved
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BonusShareAnnouncement(Base):
    __tablename__ = "bonus_share_announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    bonus_percentage = Column(Float)
    announcement_date = Column(DateTime, nullable=False)
    book_closure_date = Column(DateTime)
    source = Column(String(50))
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class DividendAnnouncement(Base):
    __tablename__ = "dividend_announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    dividend_percentage = Column(Float)
    dividend_type = Column(String(50))  # cash, stock, hybrid
    announcement_date = Column(DateTime, nullable=False)
    book_closure_date = Column(DateTime)
    source = Column(String(50))
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class RightShareAnnouncement(Base):
    __tablename__ = "right_share_announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    ratio = Column(String(50))  # e.g., "1:0.5"
    price_per_unit = Column(Float)
    announcement_date = Column(DateTime, nullable=False)
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    source = Column(String(50))
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class IPOScore(Base):
    __tablename__ = "ipo_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    ipo_id = Column(Integer, nullable=False)
    company_name = Column(String(200))
    
    # AI scoring components
    demand_score = Column(Float)  # 0-100
    financial_score = Column(Float)  # 0-100
    sector_score = Column(Float)  # 0-100
    risk_score = Column(Float)  # 0-100 (lower is better)
    oversubscription_forecast = Column(Float)  # Predicted multiple
    
    # Final scores
    overall_score = Column(Float)  # Weighted average 0-100
    recommendation = Column(String(20))  # Strong Buy, Buy, Hold, Avoid
    
    # Historical oversubscription data for training
    historical_oversubscription = Column(JSON)
    similar_ipos = Column(JSON)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)

class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50))
    task_id = Column(String(100))
    status = Column(String(20))  # success, failed, partial
    records_found = Column(Integer)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)