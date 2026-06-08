from fastapi import FastAPI, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List

from .config import settings
from .database import get_db, engine
from .models import Base, IPOAnnouncement, BonusShareAnnouncement, DividendAnnouncement, RightShareAnnouncement, IPOScore
from .workers.tasks import scrape_all_sources, update_ai_scores
from .services.scoring_engine import AIIPOEngine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="NEPSE IPO Intelligence API - Real-time IPO, Bonus, Dividend, and Right Share data with AI scoring"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI engine
ai_engine = AIIPOEngine()

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION
    }

# Trigger manual scrape
@app.post("/api/v1/scrape/trigger")
def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger scraping of all sources"""
    background_tasks.add_task(scrape_all_sources.delay)
    return {"message": "Scraping triggered", "task": "scrape_all_sources"}

# Trigger AI scoring update
@app.post("/api/v1/scores/update")
def trigger_score_update(background_tasks: BackgroundTasks):
    """Manually trigger AI score updates"""
    background_tasks.add_task(update_ai_scores.delay)
    return {"message": "Score update triggered"}

# Get IPOs with filters and AI scores
@app.get("/api/v1/ipos")
def get_ipos(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="upcoming, open, closed, approved"),
    sector: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_scores: bool = Query(True, description="Include AI scores")
):
    """Get IPO announcements with optional AI scoring"""
    
    query = db.query(IPOAnnouncement)
    
    if status:
        query = query.filter(IPOAnnouncement.status == status)
    
    if from_date:
        query = query.filter(IPOAnnouncement.announcement_date >= datetime.fromisoformat(from_date))
    
    if to_date:
        query = query.filter(IPOAnnouncement.announcement_date <= datetime.fromisoformat(to_date))
    
    if sector:
        # Simple sector filtering by company name keywords
        sector_keywords = {
            'hydropower': ['hydro', 'power', 'energy'],
            'microfinance': ['laghubitta', 'microfinance'],
            'insurance': ['insurance'],
            'bank': ['bank'],
        }
        keywords = sector_keywords.get(sector.lower(), [])
        if keywords:
            conditions = [IPOAnnouncement.company_name.ilike(f'%{kw}%') for kw in keywords]
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
    
    total = query.count()
    ipos = query.order_by(IPOAnnouncement.announcement_date.desc()).offset(offset).limit(limit).all()
    
    result = []
    for ipo in ipos:
        ipo_dict = {
            'id': ipo.id,
            'company_name': ipo.company_name,
            'announcement_date': ipo.announcement_date.isoformat() if ipo.announcement_date else None,
            'open_date': ipo.open_date.isoformat() if ipo.open_date else None,
            'close_date': ipo.close_date.isoformat() if ipo.close_date else None,
            'issue_size': ipo.issue_size,
            'units': ipo.units,
            'price_per_unit': ipo.price_per_unit,
            'issue_manager': ipo.issue_manager,
            'status': ipo.status,
            'source': ipo.source
        }
        
        if include_scores:
            score = db.query(IPOScore).filter(IPOScore.ipo_id == ipo.id).first()
            if score:
                ipo_dict['ai_score'] = {
                    'overall': score.overall_score,
                    'demand': score.demand_score,
                    'financial': score.financial_score,
                    'sector': score.sector_score,
                    'risk': score.risk_score,
                    'recommendation': score.recommendation,
                    'forecast_oversubscription': score.oversubscription_forecast
                }
            else:
                # Calculate on the fly
                scores = ai_engine.calculate_score(ipo, [])
                ipo_dict['ai_score'] = scores
        
        result.append(ipo_dict)
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": result
    }

# Get bonus shares
@app.get("/api/v1/bonus-shares")
def get_bonus_shares(
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500)
):
    query = db.query(BonusShareAnnouncement)
    
    if from_date:
        query = query.filter(BonusShareAnnouncement.announcement_date >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(BonusShareAnnouncement.announcement_date <= datetime.fromisoformat(to_date))
    
    total = query.count()
    data = query.order_by(BonusShareAnnouncement.announcement_date.desc()).limit(limit).all()
    
    return {
        "total": total,
        "data": [
            {
                'id': d.id,
                'company_name': d.company_name,
                'bonus_percentage': d.bonus_percentage,
                'announcement_date': d.announcement_date.isoformat() if d.announcement_date else None,
                'book_closure_date': d.book_closure_date.isoformat() if d.book_closure_date else None,
                'source': d.source
            }
            for d in data
        ]
    }

# Get dividends
@app.get("/api/v1/dividends")
def get_dividends(
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500)
):
    query = db.query(DividendAnnouncement)
    
    if from_date:
        query = query.filter(DividendAnnouncement.announcement_date >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(DividendAnnouncement.announcement_date <= datetime.fromisoformat(to_date))
    
    total = query.count()
    data = query.order_by(DividendAnnouncement.announcement_date.desc()).limit(limit).all()
    
    return {
        "total": total,
        "data": [
            {
                'id': d.id,
                'company_name': d.company_name,
                'dividend_percentage': d.dividend_percentage,
                'dividend_type': d.dividend_type,
                'announcement_date': d.announcement_date.isoformat() if d.announcement_date else None,
                'book_closure_date': d.book_closure_date.isoformat() if d.book_closure_date else None,
                'source': d.source
            }
            for d in data
        ]
    }

# Get right shares
@app.get("/api/v1/right-shares")
def get_right_shares(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500)
):
    data = db.query(RightShareAnnouncement).order_by(
        RightShareAnnouncement.announcement_date.desc()
    ).limit(limit).all()
    
    return {
        "total": len(data),
        "data": [
            {
                'id': d.id,
                'company_name': d.company_name,
                'ratio': d.ratio,
                'price_per_unit': d.price_per_unit,
                'announcement_date': d.announcement_date.isoformat() if d.announcement_date else None,
                'open_date': d.open_date.isoformat() if d.open_date else None,
                'close_date': d.close_date.isoformat() if d.close_date else None,
                'source': d.source
            }
            for d in data
        ]
    }

# Dashboard summary
@app.get("/api/v1/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get summary statistics for dashboard"""
    
    now = datetime.now()
    last_24h = now - timedelta(hours=24)
    
    upcoming_ipos = db.query(IPOAnnouncement).filter(
        IPOAnnouncement.status == 'upcoming'
    ).count()
    
    open_ipos = db.query(IPOAnnouncement).filter(
        IPOAnnouncement.status == 'open'
    ).count()
    
    new_announcements = db.query(IPOAnnouncement).filter(
        IPOAnnouncement.announcement_date >= last_24h
    ).count()
    
    bonus_total = db.query(BonusShareAnnouncement).count()
    dividend_total = db.query(DividendAnnouncement).count()
    
    # Get top-rated upcoming IPO
    top_ipo = db.query(IPOAnnouncement, IPOScore).join(
        IPOScore, IPOAnnouncement.id == IPOScore.ipo_id
    ).filter(
        IPOAnnouncement.status == 'upcoming'
    ).order_by(IPOScore.overall_score.desc()).first()
    
    return {
        "statistics": {
            "upcoming_ipos": upcoming_ipos,
            "open_ipos": open_ipos,
            "new_announcements_24h": new_announcements,
            "total_bonus_announcements": bonus_total,
            "total_dividend_announcements": dividend_total
        },
        "featured_ipo": {
            "company": top_ipo[0].company_name if top_ipo else None,
            "score": top_ipo[1].overall_score if top_ipo else None,
            "recommendation": top_ipo[1].recommendation if top_ipo else None,
            "forecast_oversubscription": top_ipo[1].oversubscription_forecast if top_ipo else None
        } if top_ipo else None,
        "last_updated": now.isoformat()
    }

# Search endpoint
@app.get("/api/v1/search")
def search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100)
):
    """Search across all announcements"""
    
    search_pattern = f"%{q}%"
    
    ipos = db.query(IPOAnnouncement).filter(
        IPOAnnouncement.company_name.ilike(search_pattern)
    ).limit(limit).all()
    
    bonus = db.query(BonusShareAnnouncement).filter(
        BonusShareAnnouncement.company_name.ilike(search_pattern)
    ).limit(limit).all()
    
    dividends = db.query(DividendAnnouncement).filter(
        DividendAnnouncement.company_name.ilike(search_pattern)
    ).limit(limit).all()
    
    return {
        "query": q,
        "results": {
            "ipos": len(ipos),
            "bonus_shares": len(bonus),
            "dividends": len(dividends)
        },
        "data": {
            "ipos": [{'company': i.company_name, 'date': i.announcement_date.isoformat() if i.announcement_date else None} for i in ipos],
            "bonus_shares": [{'company': b.company_name, 'bonus': b.bonus_percentage} for b in bonus],
            "dividends": [{'company': d.company_name, 'dividend': d.dividend_percentage} for d in dividends]
        }
    }