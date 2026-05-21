from apscheduler.schedulers.background import BackgroundScheduler
from newspulse.fetcher import run_all
from newspulse.classifier import classify_pending

def start():
    scheduler = BackgroundScheduler()

    scheduler.add_job(run_all, 'interval', minutes = 30)
    scheduler.add_job(classify_pending, 'interval', minutes = 35)
    
    scheduler.start()
