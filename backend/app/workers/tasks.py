from celery import Task
from .celery_app import celery_app
from ..database import SessionLocal
from ..models import IPOAnnouncement, ScrapingLog, IPOScore
from ..scrapers.merolagani import MerolaganiScraper
from ..scrapers.sharesansar import ShareSansarScraper
from ..scrapers.sebon import SEBONScraper
from ..services.scoring_engine import AIIPOEngine
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ScrapingTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        db = SessionLocal()
        try:
            log = db.query(ScrapingLog).filter_by(task_id=task_id).first()
            if log:
                log.status = "failed"
                log.error_message = str(exc)
                db.commit()
        finally:
            db.close()

@celery_app.task(base=ScrapingTask, bind=True)
def scrape_merolagani(self):
    """Scrape IPO data from Merolagani"""
    start_time = datetime.utcnow()
    db = SessionLocal()
    
    try:
        # Create log entry
        log = ScrapingLog(
            source="merolagani",
            task_id=self.request.id,
            status="running",
            started_at=start_time
        )
        db.add(log)
        db.commit()
        
        # Run scraper
        scraper = MerolaganiScraper()
        data = scraper.scrape()
        
        # Store in database
        records = 0
        for item in data.get('ipos', []):
            ipo = IPOAnnouncement(
                company_name=item['company'],
                announcement_date=datetime.strptime(item['date'], '%Y/%m/%d'),
                issue_size=item.get('issue_size'),
                source="merolagani",
                raw_announcement=item['announcement'],
                status=item.get('status', 'upcoming')
            )
            db.merge(ipo)
            records += 1
        
        db.commit()
        
        # Update log
        log.status = "success"
        log.records_found = records
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        db.commit()
        
        return {"source": "merolagani", "records": records, "status": "success"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Merolagani scraping failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(base=ScrapingTask, bind=True)
def scrape_sharesansar(self):
    """Scrape IPO data from ShareSansar"""
    start_time = datetime.utcnow()
    db = SessionLocal()
    
    try:
        log = ScrapingLog(
            source="sharesansar",
            task_id=self.request.id,
            status="running",
            started_at=start_time
        )
        db.add(log)
        db.commit()
        
        scraper = ShareSansarScraper()
        data = scraper.scrape()
        
        records = 0
        for item in data.get('bonus_shares', []):
            bonus = BonusShareAnnouncement(
                company_name=item['company'],
                bonus_percentage=item.get('percentage'),
                announcement_date=datetime.strptime(item['date'], '%Y/%m/%d'),
                source="sharesansar",
                raw_text=item['announcement']
            )
            db.merge(bonus)
            records += 1
        
        db.commit()
        
        log.status = "success"
        log.records_found = records
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        db.commit()
        
        return {"source": "sharesansar", "records": records, "status": "success"}
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task(base=ScrapingTask, bind=True)
def scrape_sebon_pipeline(self):
    """Scrape SEBON IPO pipeline data"""
    start_time = datetime.utcnow()
    db = SessionLocal()
    
    try:
        log = ScrapingLog(
            source="sebon",
            task_id=self.request.id,
            status="running",
            started_at=start_time
        )
        db.add(log)
        db.commit()
        
        scraper = SEBONScraper()
        data = scraper.scrape()
        
        records = 0
        for item in data.get('pipeline', []):
            ipo = IPOAnnouncement(
                company_name=item['company'],
                announcement_date=datetime.utcnow(),
                status="approved" if item.get('approved') else "pipeline",
                source="sebon",
                raw_announcement=item['details']
            )
            db.merge(ipo)
            records += 1
        
        db.commit()
        
        log.status = "success"
        log.records_found = records
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        db.commit()
        
        return {"source": "sebon", "records": records, "status": "success"}
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task
def scrape_all_sources():
    """Run all scrapers in parallel"""
    from celery import group
    
    job = group(
        scrape_merolagani.s(),
        scrape_sharesansar.s(),
        scrape_sebon_pipeline.s()
    )
    
    result = job.apply_async()
    return result.get()

@celery_app.task
def update_ai_scores():
    """Update AI scoring for all active IPOs"""
    db = SessionLocal()
    engine = AIIPOEngine()
    
    try:
        # Get active IPOs
        ipos = db.query(IPOAnnouncement).filter(
            IPOAnnouncement.status.in_(['upcoming', 'open'])
        ).all()
        
        scores_updated = 0
        for ipo in ipos:
            # Get similar IPOs for context
            similar_ipos = db.query(IPOAnnouncement).filter(
                IPOAnnouncement.company_name.ilike(f"%{ipo.company_name.split()[0]}%")
            ).limit(10).all()
            
            # Calculate AI scores
            scores = engine.calculate_score(ipo, similar_ipos)
            
            # Store or update score
            existing = db.query(IPOScore).filter_by(ipo_id=ipo.id).first()
            if existing:
                for key, value in scores.items():
                    setattr(existing, key, value)
                existing.calculated_at = datetime.utcnow()
            else:
                new_score = IPOScore(ipo_id=ipo.id, **scores)
                db.add(new_score)
            
            scores_updated += 1
        
        db.commit()
        return {"scores_updated": scores_updated}
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task
def cleanup_logs():
    """Clean up old logs (keep last 30 days)"""
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        deleted = db.query(ScrapingLog).filter(
            ScrapingLog.created_at < cutoff
        ).delete()
        
        db.commit()
        return {"deleted_logs": deleted}
    finally:
        db.close()