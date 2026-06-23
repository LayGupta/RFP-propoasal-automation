"""
scheduler.py — APScheduler cron job for proactive tender scouting

Daily at 6:00 AM IST (00:30 UTC).
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.scout_service import scout_and_alert

logger = logging.getLogger("scheduler")

_scheduler = BackgroundScheduler()
_started = False


def start_scheduler():
    global _started
    if _started:
        return
    trigger = CronTrigger(hour=0, minute=30)
    _scheduler.add_job(scout_and_alert, trigger, id="tender_scout", replace_existing=True)
    _scheduler.start()
    _started = True
    logger.info("Scout scheduler started (daily 6:00 AM IST)")


def stop_scheduler():
    global _started
    if _started:
        _scheduler.shutdown(wait=False)
        _started = False
