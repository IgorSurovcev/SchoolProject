from flask import Flask
import config
from utils.utils import *
from utils.scheduler import scheduler
from routers import routers_app



app = Flask(__name__)
app.secret_key = config.secret_key

app.register_blueprint(routers_app)


scheduler.add_job(id='job_every_week', func=job_every_week, trigger='cron', day_of_week=0, hour=3, jobstore='mongo', replace_existing=True, misfire_grace_time=300).id



app.jinja_env.globals.update(get_top=get_top, get_abonement=get_abonement, get_intervals=get_intervals, get_is_free_day=get_is_free_day, get_is_time_in_schedule=get_is_time_in_schedule, get_isnot_free_day_timetable=get_isnot_free_day_timetable, get_teachers_by_subject=get_teachers_by_subject, get_studied_subject=get_studied_subject, get_stripe=get_stripe)



if __name__ == "__main__":
    app.run(debug=True, port=5050)






