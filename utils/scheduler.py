from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.schedulers.background import BackgroundScheduler


from utils.database import db



jobstores = {'mongo': MongoDBJobStore(client=db.client, database='school_db', collection='jobs')}
job_defaults = {'coalesce': False,'max_instances': 100}
scheduler = BackgroundScheduler(jobstores=jobstores, job_defaults=job_defaults, timezone='Europe/Moscow')

scheduler.start()
