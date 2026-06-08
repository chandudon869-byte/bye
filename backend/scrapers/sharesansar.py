from .base import BaseScraper
import re
import hashlib
from datetime import datetime


class ShareSansarScraper(BaseScraper):
    """Production-ready ShareSansar scraper"""

    # =========================
    # MAIN SCRAPE METHOD
    # =========================

    def scrape(self):

        results = {
            "ipos": [],
            "floorsheet": [],
            "bonus_shares": []
        }

        # =========================
        # 1. UPCOMING ISSUES (JSON API - BEST SOURCE)
        # =========================

        url = (
            "https://www.sharesansar.com/"
            "upcoming-issue"
            "?draw=1&start=0&length=50&type=1"
        )

        response = self.fetch_page(url)

        if response:
            try:
                data = response.json()

                for item in data.get("data", []):
                    company = self._clean(item.get("company", {}).get("companyname", ""))
                    symbol = item.get("company", {}).get("symbol", "")
                    ratio = item.get("ratio_value", "")
                    units = item.get("total_units", "")
                    amount = item.get("amount", "")
                    open_date = item.get("application_date", "")
                    sebon_date = item.get("date_sebon", "")
                    issue_manager = item.get("issue_manager", "")

                    base = {
                        "company": company,
                        "symbol": symbol,
                        "ratio": ratio,
                        "units": units,
                        "amount": amount,
                        "open_date": open_date,
                        "sebon_date": sebon_date,
                        "issue_manager": issue_manager,
                        "external_id": self._make_id(company, open_date, ratio)
                    }

                    results["ipos"].append(base)

            except Exception:
                # fallback silently (don’t crash scraper)
                pass

        # =========================
        # 2. FLOOR SHEET (LIGHTWEIGHT PARSING ONLY)
        # =========================

        fs_url = "https://www.sharesansar.com/floorsheet"
        fs_response = self.fetch_page(fs_url)

        if fs_response:
            try:
                # avoid pandas (unstable)
                import re

                rows = re.findall(
                    r"<tr>(.*?)</tr>",
                    fs_response.text,
                    re.DOTALL
                )

                for row in rows[:50]:
                    cols = re.findall(r"<t[dh]>(.*?)</t[dh]>", row, re.DOTALL)

                    if len(cols) < 5:
                        continue

                    results["floorsheet"].append({
                        "contract_no": self._clean(cols[0]),
                        "stock": self._clean(cols[1]),
                        "buyer": self._clean(cols[2]),
                        "seller": self._clean(cols[3]),
                        "quantity": self._clean(cols[4]),
                        "external_id": self._make_id(cols[0], cols[1], cols[2])
                    })

            except Exception:
                pass

        return results

    # =========================
    # HELPERS
    # =========================

    def _clean(self, value):
        if not value:
            return ""
        return str(value).strip()

    def _make_id(self, *args):
        """Dedup key for PostgreSQL"""
        raw = "-".join([str(a) for a in args if a])
        return hashlib.md5(raw.encode()).hexdigest()