from .base import BaseScraper
import re
from datetime import datetime


class MerolaganiScraper(BaseScraper):
    """Production-ready Merolagani scraper"""

    def scrape(self):
        year = datetime.today().year

        url = (
            "https://merolagani.com/handlers/webrequesthandler.ashx"
            f"?type=stock_event&fromDate=1%2F1%2F{year}&toDate=12%2F31%2F{year}"
        )

        response = self.fetch_page(url)

        if not response:
            return self._empty_result()

        # 🔒 safe JSON parsing
        try:
            data = response.json()
        except Exception:
            return self._empty_result()

        results = {
            "ipos": [],
            "bonus_shares": [],
            "dividends": [],
            "right_shares": []
        }

        for item in data.get("detail", []):
            detail = item.get("announcementDetail", "")
            if not detail:
                continue

            detail_lower = detail.lower()
            date = item.get("actionDate", "")

            company = self._extract_company(detail)

            base = {
                "company": company,
                "date": date,
                "announcement": detail,
                "external_id": self._make_id(company, date, detail)
            }

            # ======================
            # IPO
            # ======================
            if any(x in detail_lower for x in ["ipo", "initial public offering", "public issue", "fpo"]):
                size_match = re.search(r"([\d,]+)\s*units", detail_lower)

                if size_match:
                    base["issue_size"] = int(size_match.group(1).replace(",", ""))

                results["ipos"].append(base)

            # ======================
            # BONUS
            # ======================
            elif "bonus" in detail_lower:
                pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*bonus", detail_lower)

                if pct_match:
                    base["percentage"] = float(pct_match.group(1))

                results["bonus_shares"].append(base)

            # ======================
            # DIVIDEND
            # ======================
            elif "dividend" in detail_lower:
                pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*dividend", detail_lower)

                if pct_match:
                    base["percentage"] = float(pct_match.group(1))

                results["dividends"].append(base)

            # ======================
            # RIGHT SHARES
            # ======================
            elif "right share" in detail_lower or "rights share" in detail_lower:
                ratio_match = re.search(r"(\d+)\s*:\s*(\d+(?:\.\d+)?)", detail_lower)

                if ratio_match:
                    base["ratio"] = f"{ratio_match.group(1)}:{ratio_match.group(2)}"

                results["right_shares"].append(base)

        return results

    # ======================
    # Helpers
    # ======================

    def _empty_result(self):
        return {
            "ipos": [],
            "bonus_shares": [],
            "dividends": [],
            "right_shares": []
        }

    def _make_id(self, company, date, text):
        """Dedup key for PostgreSQL"""
        import hashlib
        raw = f"{company}-{date}-{text}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _extract_company(self, text):
        patterns = [
            r"^([^-]+?)(?:\s+has|\s+is|\s+will|\s+announced|\s+notified|\s+limited)",
            r"^([^-]+?)(?:\s+to|\s+for|\s+-\s+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                if 3 < len(company) < 100:
                    return company

        return text[:60].strip()