-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create indexes for performance
CREATE INDEX idx_ipo_announcement_date ON ipo_announcements(announcement_date);
CREATE INDEX idx_ipo_company_name ON ipo_announcements(company_name);
CREATE INDEX idx_ipo_status ON ipo_announcements(status);

CREATE INDEX idx_bonus_announcement_date ON bonus_share_announcements(announcement_date);
CREATE INDEX idx_dividend_announcement_date ON dividend_announcements(announcement_date);

-- Create view for upcoming IPOs with scores
CREATE VIEW upcoming_ipos_with_scores AS
SELECT 
    i.id,
    i.company_name,
    i.announcement_date,
    i.open_date,
    i.close_date,
    i.issue_size,
    i.status,
    s.overall_score,
    s.recommendation,
    s.oversubscription_forecast
FROM ipo_announcements i
LEFT JOIN ipo_scores s ON i.id = s.ipo_id
WHERE i.status IN ('upcoming', 'open')
ORDER BY s.overall_score DESC NULLS LAST;