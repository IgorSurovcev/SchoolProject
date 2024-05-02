from flask import Flask, render_template, url_for, request, redirect, session, Blueprint
import traceback
import random
import json
import requests
from datetime import datetime, timedelta
from nptime import nptime

from google.oauth2.credentials import Credentials
from gcsa.google_calendar import GoogleCalendar
from gcsa.conference import ConferenceSolutionCreateRequest, SolutionType
from gcsa.reminders import EmailReminder, PopupReminder
from google.auth.transport.requests import Request
from gcsa.event import Event

from dateutil.relativedelta import relativedelta
from utils.utils import first_event, second_event



from utils.scheduler import scheduler
import config
from utils.utils import *

routers_app = Blueprint('main', __name__)



def check_credentials(username, password):
    if username in config.users and config.users[username] == password:
        return True
    return False



@routers_app.route('/', methods=['POST','GET'])
def home():
    return {}

@routers_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if check_credentials(username, password):
            # Устанавливаем сессию для авторизованного пользователя
            session['username'] = username
            return redirect('/timetable')
        else:
            return 'Invalid username or password'

    return '''
        <form method="POST">
            <input type="text" name="username" placeholder="Username"><br>
            <input type="password" name="password" placeholder="Password"><br>
            <input type="submit" value="Log In">
        </form>
    '''




@routers_app.route('/logout')
def logout():
    # Очищаем сессию
    session.pop('username', None)
    return redirect('/login')


@routers_app.route('/meeting_link/<string:meeting_id>', methods=['POST','GET'])
def redirect_on_meeting(meeting_id):
    record = db.records_base.find_one({'meeting_link_for_student':f'https://{config.HOSTNAME}/meeting_link/{meeting_id}'})
    db.records_base.update_one({'_id':record['_id']},{ "$set": { 'status_record': 'Клиент пришел' }})
    
    return redirect(record['meeting_link_for_teacher'])



@routers_app.route('/pay/<string:transaction_id>', methods=['POST','GET'])
def redirect_on_sbp_link(transaction_id):
    try:

        transaction = db.transactions_base.find_one({'_id': int(transaction_id)})

        if transaction['status'] == 'Оплачено':
            return 'Оплата уже была произведена по этой ссылке'

        link = transaction['payment_link']

        client = db.clients_base.find_one({'_id': transaction['client_id']})

        if client.get('default_bank') != None:
            link = db.bank_codes[client['default_bank']] + link[5:]
        
        return redirect(link)

    except:
        logger('error', message = traceback.format_exc())


@routers_app.route('/GET_PAYMENT_STATUS_CHANGES', methods=['POST'])
def GET_PAYMENT_STATUS_CHANGES():
    try:
        data = request.get_json()
        print(data)
        transaction_id = int(data['OrderId'])
        transaction = db.transactions_base.find_one({'_id':transaction_id})

        if data['Status'] == 'CONFIRMED':
            if transaction['type'] == 'Оплата урока' and transaction['status'] == 'Ожидание оплаты':
                db.transactions_base.update_one({'_id':transaction_id},{ "$set": { 'status':'Оплачено' }})

                for record_id in transaction['record_id']:
                    db.records_base.update_one({'_id':record_id},{ "$set": { 'status_payment': 'Оплачено разово' }})

                logger('info', type='Оплата урока', way='Перевод', client_id=transaction['client_id'], amount=transaction['amount'], transaction_id=transaction['_id'])
            


            elif transaction['type'] == 'Оплата абонемента' and transaction['status'] == 'Ожидание оплаты':
                client = db.clients_base.find_one({'_id':transaction['client_id']})
                abonements = client['abonements']
                abonement = int(abonements.get(transaction['subject'], '0'))

                records = list(db.records_base.find({'status_payment': 'Не оплачен', 'timestart': {'$lt': datetime.now()}, 'student_id':client['_id']}).sort('timestart', 1))
                if records != []:
                    for record in records:
                        abonement -= 1
                        db.records_base.update_one({'_id':record['_id']},{ "$set": { 'status_payment': 'Оплачено абонементом' }})
   
                abonements.update({transaction['subject']:str(int(abonement)+10)})

                db.clients_base.update_one({'_id':transaction['client_id']},{ "$set": { 'abonements': abonements}})
                db.transactions_base.update_one({'_id':transaction_id},{ "$set": { 'status':'Оплачено' }})

                text = 'Оплата прошла успешно, абонемент зачислен'
                requests.get('http://127.0.0.1:5055/send_message', timeout=10, params={'user_id':transaction['tg_id'],'text':text})


                logger('info', type='Покупка абонемента', client_id=transaction['client_id'], description=transaction['description'], amount=transaction['amount'], transaction_id=transaction['_id'])

            else:
                logger('error', message = 'Оплачена оплаченная вещь!! '+str(transaction['record_id']))
                return 'OK'
                
        return 'OK'
    except:
        logger('error', message = traceback.format_exc())
        # ПРИ ПРОДЕ УБРАТЬ
        return 'OK'


# Clients
@routers_app.route('/clients', methods=['GET'])
def clients():
    if 'username' not in session:
        return redirect('/login')
    
    clients = list(db.clients_base.find({}))

    return render_template('clients.html',clients=reversed(clients), subjects=db.subjects)

@routers_app.route('/clients/create', methods=['POST'])
def client_create():
    try:
        id = random.randint(1000000,9999999)
        phone = request.form['phone']
        mail = request.form['mail']
        fullname = request.form['fullname']
        parents_fullname = request.form.get('parents_fullname', '')
        timezone = request.form['timezone']
        grade = request.form['grade']
        parents_username_tg = request.form['parents_username_tg']
        students_username_tg = request.form['students_username_tg']
        tg_ids = request.form['tg_ids'].split(' ')
        abonements = {subject: 0 for subject in db.subjects}
        studied_subjects = []
        tags = [tag for tag in request.form.get('tags', '').split(' ')]
        info = request.form.get('info' , '')

        db.clients_base.insert_one({
            '_id': id,
            'phone': phone,
            'mail': mail,
            'fullname' : fullname,
            'parents_fullname': parents_fullname,
            'timezone': timezone,
            'grade': grade,
            'parents_username_tg': parents_username_tg,
            'students_username_tg': students_username_tg,
            'tg_ids': tg_ids,
            'abonements' : abonements,
            'studied_subjects': studied_subjects,
            'tags': tags,
            'info': info
        })
        return redirect('/clients')
    
    except:
        logger('error', message = traceback.format_exc())

@routers_app.route('/clients/delete/<int:id>', methods=['GET'])
def client_delite(id):
    db.clients_base.delete_one({'_id':int(id)})
    print(id)
    return redirect('/clients')

@routers_app.route('/clients/edit/<int:id>', methods=['POST'])
def client_edit(id):
    try:
        # id = random.randint(1000000,9999999)
        phone = request.form['phone']
        mail = request.form['mail']
        fullname = request.form['fullname']
        parents_fullname = str(request.form.get('parents_fullname'))
        timezone = request.form['timezone']
        grade = request.form['grade']
        parents_username_tg = request.form['parents_username_tg']
        students_username_tg = request.form['students_username_tg']
        tg_ids = request.form['tg_ids'].split(' ')
        tags = [tag for tag in request.form.get('tags', '').split(' ')]
        info = request.form.get('info' , '')

        abonements = {}
        for item in list(request.form):
            if item.split('---')[0] == 'abonement': 
                abonements.update({item.split('---')[1]: request.form[item]})

        studied_subjects = {}
        for subject in db.subjects:
            teacher_id_for_subject = request.form[f'teacher_id_for_student---{subject}']
            if teacher_id_for_subject != 'None':
                studied_subjects.update({subject:int(teacher_id_for_subject)})


        db.clients_base.update_one({'_id':int(id)},{ "$set": {
                                                'phone': phone,
                                                'mail': mail,
                                                'fullname' : fullname,
                                                'parents_fullname': parents_fullname,
                                                'timezone': timezone,
                                                'grade': grade,
                                                'parents_username_tg': parents_username_tg,
                                                'students_username_tg': students_username_tg,
                                                'tg_ids': tg_ids,
                                                'abonements': abonements,
                                                'studied_subjects': studied_subjects,
                                                'tags': tags,
                                                'info': info
                                            }})
        return redirect('/clients')
    
    except:
        logger('error', message = traceback.format_exc())

# TEACHERS
@routers_app.route('/teachers', methods=['GET'])
def teachers_main():
    if 'username' not in session:
        return redirect('/login')
    
    teachers_data = list(db.teachers_base.find({}))
    return render_template('teachers.html',data=reversed(teachers_data),subjects=db.subjects)

@routers_app.route('/teachers/create', methods=['POST'])
def teacher_create():
    try:
        id = random.randint(10000,99999)
        phone = request.form['phone']
        fullname = request.form['fullname']
        id_tg = request.form['id_tg']
        username_tg = request.form['username_tg']
        timezone = request.form['timezone']
        token = request.form['token']
        spec = request.form.getlist('spec')
        rank = request.form['rank']
        work_schedule = {'working_times': [[],[],[],[],[],[],[]], 'free_days': []}

        db.teachers_base.insert_one({
            '_id': id,
            'phone': phone,
            'fullname' : fullname,
            'id_tg': id_tg,
            'timezone': timezone,
            'username_tg': username_tg,
            'token': token,
            'spec': spec,
            'rank': rank,
            'work_schedule': work_schedule
        })
        return redirect('/teachers')
    
    except:
        logger('error', message = traceback.format_exc())

@routers_app.route('/teachers/delete/<int:id>', methods=['GET'])
def teacher_delite(id):
    db.teachers_base.delete_one({'_id':int(id)})
    return redirect('/teachers')

@routers_app.route('/teachers/edit/<int:id>', methods=['POST'])
def teacher_edit(id):
    try:
        shift = request.args.get('shift', default = None, type = int)
        # id = random.randint(10000,99999)
        # print(request.form)

        phone = request.form.get('phone')
        fullname = request.form.get('fullname')
        id_tg = request.form.get('id_tg')
        username_tg = request.form.get('username_tg')
        timezone = request.form.get('timezone')
        token = request.form.get('token')
        spec = request.form.getlist('spec')
        rank = request.form.get('rank')

        work_schedule = db.teachers_base.find_one({'_id':id}).get('work_schedule')
        if work_schedule == None: work_schedule = {'working_times': [[],[],[],[],[],[],[]], 'free_days': []}

        if request.form.get('date_working_time') != None:
            date_working_time = request.form['date_working_time'].split('.')
            date_working_time = datetime(int(date_working_time[0]),int(date_working_time[1]),int(date_working_time[2]))
            weekday_working_time = date_working_time.weekday()
            print(weekday_working_time)

            working_times = set()
            for i in range(6):
                working_hours_start = request.form.get(f'working_hours_start_{i}')
                working_hours_end = request.form.get(f'working_hours_end_{i}')
                if working_hours_start == None: break
                working_hours_start = nptime(hour=int(working_hours_start.split(':')[0]), minute=int(working_hours_start.split(':')[1]))
                working_hours_end = nptime(hour=int(working_hours_end.split(':')[0]), minute=int(working_hours_end.split(':')[1]))
                time = working_hours_start
                if len(str(time.minute))==1: working_times.add(f'{time.hour}:{time.minute}0')
                else: working_times.add(f'{time.hour}:{time.minute}')
                ended = False
                while not(ended):
                    time += timedelta(minutes=15)
                    
                    if time < working_hours_end: 
                        if len(str(time.minute))==1: working_times.add(f'{time.hour}:{time.minute}0')
                        else: working_times.add(f'{time.hour}:{time.minute}')
                    else: 
                        if len(str(time.minute))==1: working_times.add(f'{time.hour}:{time.minute}0')
                        else: working_times.add(f'{time.hour}:{time.minute}')
                        ended = True
            work_schedule['working_times'][weekday_working_time] = list(working_times)
            if request.form.get('free_day') != None:
                free_days = set(work_schedule['free_days'])
                free_days.add(f'{date_working_time.year}.{date_working_time.month}.{date_working_time.day}')
                work_schedule['free_days'] = list(free_days)
            else:
                if f'{date_working_time.year}.{date_working_time.month}.{date_working_time.day}' in work_schedule['free_days']:
                    work_schedule['free_days'].remove(f'{date_working_time.year}.{date_working_time.month}.{date_working_time.day}')
                

        updates = {'phone': phone, 'fullname' : fullname,'id_tg': id_tg,'timezone': timezone,'username_tg': username_tg,'token': token,'spec': spec,'rank': rank, 'work_schedule': work_schedule}

        finish_updates = updates.copy()
        for update in updates: 
            if updates[update] == None or updates[update] == []: finish_updates.pop(update)

        print(finish_updates)
        db.teachers_base.update_one({'_id':int(id)},{ "$set": finish_updates})

        
        if shift==None:
            return redirect('/teachers')
        else:
            return redirect(f'/timetable?teacher_id={id}&shift={shift}')
    
    except:
        logger('error', message = traceback.format_exc())

@routers_app.route('/teachers/calculate_salary/', methods=['POST'])
def teacher_calculate_salary():
    shift = request.args.get('shift', default = None, type = int)
    teacher_id = request.args.get('teacher_id', default = 0, type = int)

    records = db.records_base.find({'teacher_id': teacher_id,})

    # return redirect('/teachers')

# RECORDS
@routers_app.route('/records', methods=['GET'])
def records_main():
    if 'username' not in session:
        return redirect('/login')
    try:

        records_data = list(db.records_base.find({}))
        teachers_data = list(db.teachers_base.find({}))
        clients_data = list(db.clients_base.find({}))
        for record in records_data:
            record.update({'teachers_fullname':db.teachers_base.find_one({'_id':record['teacher_id']})['fullname']})
            client = db.clients_base.find_one({'_id':record['student_id']})
            if client == None: 
                clients_fullname = 'Not found'
                grade = 'Not found'
            else:
                clients_fullname = client['fullname']
                grade = client['grade']
            record.update({'students_fullname':clients_fullname})
        return render_template('records.html',records_data=records_data, teachers_data=teachers_data, clients_data=clients_data, subjects=db.subjects)
    
    except:
        logger('error', message = traceback.format_exc())

@routers_app.route('/records/create', methods=['POST'])
def record_create():
    try:
        teacher_id_page = request.args.get('teacher_id', default = 0, type = int)
        shift = request.args.get('shift', default = 0, type = int)

        record_id = random.randint(10000000,99999999)

        teacher_id = int(request.form['teacher_id'])
        student_id = int(request.form['student_id'])
        subject = request.form['subject']
        date = request.form['date']
        # if len(request.form['date'].split('-')[2]) == 1: date = request.form['date'].split('-')[0] + request.form['date'].split('-')[1] + '0' + request.form['date'].split('-')[2]
        time = request.form['time']
        timestart = datetime(int(date.split('-')[0]),int(date.split('-')[1]),int(date.split('-')[2]),int(time.split(':')[0]),int(time.split(':')[1]))
        full_date = datetime(int(date.split('-')[0]),int(date.split('-')[1]),int(date.split('-')[2]))
        duration = int(request.form['duration'])
        price = int(request.form['price'])
        teachers_fee = int(request.form['teachers_fee'])

        status_record = 'В ожидании клиента'
        status_payment = 'Не оплачен'
        status_payment_to_teacher = 'Не оплачено'
        # JOBS
        client = db.clients_base.find_one({'_id':student_id})
        # clients_timezone = int(client['timezone'])

        job1 = scheduler.add_job(func=first_event, id=f'{record_id}_job1', trigger='date', run_date= timestart + timedelta(hours=-6), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
        job2 = scheduler.add_job(func=second_event, id=f'{record_id}_job2', trigger='date', run_date= timestart + timedelta(minutes=duration), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id

        # job1 = scheduler.add_job(func=first_event, id=f'{record_id}_job1', trigger='date', run_date= datetime.now() + timedelta(seconds=5, hours=-2), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
        # job2 = scheduler.add_job(func=second_event, id=f'{record_id}_job2', trigger='date', run_date= datetime.now() + timedelta(seconds=10, hours=-2), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id

        # GOOGLE CALENDAR AND MEETING
        teacher = db.teachers_base.find_one({'_id': teacher_id})
        token = json.loads(teacher['token'])

        credentials = Credentials(token=token['token'], refresh_token=token['refresh_token'], client_id=token['client_id'], client_secret=token['client_secret'], scopes=token['scopes'], token_uri=token['token_uri'], expiry=token['expiry'])
        credentials.refresh(Request())
        db.teachers_base.update_one({"_id": teacher_id}, {"$set": {'token': credentials.to_json()}}) # UPDATE TOKEN IN BASE

        gc = GoogleCalendar(credentials=credentials)
        conference_solution=ConferenceSolutionCreateRequest(solution_type=SolutionType.HANGOUTS_MEET)

        fullname = client['fullname'].split(' ')[1]
        grade = client['grade'] + ' класс'

        teachers_time_zone = int(teacher['timezone'])

        teachers_time_start = timestart + timedelta(hours=teachers_time_zone)
        teachers_time_end = teachers_time_start + timedelta(minutes=duration)

        event = Event(summary=fullname+' || '+grade+' || '+subject, start=teachers_time_start, end=teachers_time_end, timezone = f'Etc/GMT{-3-teachers_time_zone}', reminders=PopupReminder(minutes_before_start=25), conference_solution=conference_solution, color_id=7, event_id = random.randint(10000000,19999999)) # description = location)
        gc.add_event(event)
        google_event_id = event.event_id
        event = gc.get_event(google_event_id)
        conference_id = event.conference_solution.conference_id

        meeting_link_for_student = f'https://{config.HOSTNAME}/meeting_link/'+str(conference_id)
        meeting_link_for_teacher = 'https://meet.google.com/'+str(conference_id)
        link_to_record = ''

        if request.form.get('create_template', None) == None:
            template_id = 'None'
        else:
            template_id = random.randint(1000000,9999999)
            template = {
                '_id': template_id,
                'teacher_id': teacher_id,
                'student_id': student_id,
                'subject' : subject,
                'weekday': timestart.weekday(),
                'time': time,
                'duration': duration,
                'price': price,
                'teachers_fee': teachers_fee,
            }
            db.records_templates_base.insert_one(template)
            weeks = []
            # now = datetime.now() - timedelta(hours=2)
            monday_date = timestart - timedelta(days=timestart.weekday(), hours=timestart.hour, minutes=timestart.minute, seconds=timestart.second, microseconds=timestart.microsecond)
            weeks.append(monday_date + timedelta(weeks=1))
            weeks.append(monday_date + timedelta(weeks=2))

            create_records_by_template(template_id, weeks)

        db.records_base.insert_one({
            '_id': record_id,
            'template_id': template_id,
            'teacher_id': teacher_id,
            'student_id': student_id,
            'subject' : subject,
            'date': date,
            'time': time,
            'timestart': timestart,
            'creation_time' : datetime.now(),
            "full_date": full_date,
            'duration': duration,
            'price': price,
            'teachers_fee': teachers_fee,
            'status_record' : status_record,
            'status_payment' : status_payment,
            'status_payment_to_teacher' : status_payment_to_teacher,
            'meeting_link_for_student': meeting_link_for_student,
            'meeting_link_for_teacher': meeting_link_for_teacher,
            'link_to_record': link_to_record,
            'job1' : job1,
            'job2' : job2,
            'canceled': False,
            'google_event_id': google_event_id
        })

        if teacher_id_page==0 and shift==0:
            return redirect('/records')
        else:
            return redirect(f'/timetable?teacher_id={teacher_id_page}&shift={shift}')
        
    except:
        logger('error', message = traceback.format_exc())

@routers_app.route('/records/delete/<int:record_id>', methods=['GET'])
def record_delite(record_id):
    try:
        teacher_id_page = request.args.get('teacher_id', default = 0, type = int)
        shift = request.args.get('shift', default = 0, type = int)
        template_id = request.args.get('template_id', default = 'None', type=str)
        print(record_id)
        print(template_id)

        if template_id == 'None':
            records = [db.records_base.find_one({'_id': int(record_id)}) ]
        else:
            records = list(db.records_base.find({'template_id': int(template_id)}) )
            choused_record = db.records_base.find_one({'_id': int(record_id)})
        print(records)
        for record in records:
            if record == [None]: continue
            if template_id != 'None': 
                if record['timestart'] < choused_record['timestart']: continue

            record_id = record['_id']
            event_id =record['google_event_id']
            teacher = db.teachers_base.find_one({'_id':record['teacher_id']})
            
            token = json.loads(teacher['token'])
            teachers_time_zone = int(teacher['timezone'])
            
            credentials = Credentials(token=token['token'], refresh_token=token['refresh_token'], client_id=token['client_id'], client_secret=token['client_secret'], scopes=token['scopes'], token_uri=token['token_uri'], expiry=token['expiry'])
            credentials.refresh(Request())
            db.teachers_base.update_one({"_id": record['teacher_id']}, {"$set": {'token': credentials.to_json()}}) 

            gc = GoogleCalendar(credentials=credentials)
            try:
                event = gc.get_event(event_id)
                event.summary = '(ОТМЕНЕН) '+event.summary
                event.color_id = 8
                gc.update_event(event)
            except: None

            db.records_base.delete_one({'_id':int(record_id)})
            if template_id != 'None':
                db.records_templates_base.delete_one({'_id':int(template_id)})

        if teacher_id_page==0 and shift==0:
            return redirect('/records')
        else:
            return redirect(f'/timetable?teacher_id={teacher_id_page}&shift={shift}')

    except:
        logger('error', message = traceback.format_exc())

@routers_app.route('/records/edit/<int:id>', methods=['POST'])
def record_edit(id):
    try:
        record_id = id
        # id = random.randint(10000,99999)
        teacher_id_page = request.args.get('teacher_id', default = 0, type = int)
        shift = request.args.get('shift', default = 0, type = int)

        template_id = request.form['template_id']

        if template_id != 'None' and template_id != '' and template_id != None: template_id = int(template_id)

        # GET DATA FROM FORM
        teacher_id = int(request.form['teacher_id'])
        student_id = int(request.form['student_id'])
        subject = request.form['subject']

        time = request.form['time']
        date = request.form['date']

        timestart = datetime(int(date.split('-')[0]),int(date.split('-')[1]),int(date.split('-')[2]),int(time.split(':')[0]),int(time.split(':')[1]))
        full_date = timestart - timedelta(hours=timestart.hour, minutes=timestart.minute)

        duration = int(request.form['duration'])
        price = int(request.form['price'])
        teachers_fee = int(request.form['teachers_fee'])

        status_record = request.form['status_record']
        status_payment = request.form['status_payment']
        status_payment_to_teacher = request.form['status_payment_to_teacher']

        # CHANGE RECORDs 
        if template_id == 'None' or template_id == '':
            records = list(db.records_base.find({'_id': int(record_id)}))
        else:
            records = list(db.records_base.find({'template_id': template_id}) )
            choused_record = db.records_base.find_one({'_id': int(record_id)})

            time_change = choused_record['timestart'] - timestart

        # print(records)
        for record in records:
            if record == [None]: continue
            old_record = db.records_base.find_one({'_id':record['_id']})

            if template_id != 'None' and template_id != '': 
                if record['timestart'] < choused_record['timestart']: continue

                timestart =  old_record['timestart'] - time_change
                full_date = timestart - timedelta(hours=timestart.hour, minutes=timestart.minute)
                time = f'{timestart.hour}:{get_beauty_minutes(timestart.minute)}'
                date = f'{timestart.year}-{get_beauty_minutes(timestart.month)}-{get_beauty_minutes(timestart.day)}'

            # clients_timezone = int(clients_base.find_one({'_id':student_id})['timezone'])

            job1 = scheduler.add_job(func=first_event, id=f'{record["_id"]}_job1', trigger='date', run_date= timestart + timedelta(hours=-6), args=[record["_id"]], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
            job2 = scheduler.add_job(func=second_event, id=f'{record["_id"]}_job2', trigger='date', run_date= timestart + timedelta(minutes=duration), args=[record["_id"]], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id

            # job1 = scheduler.add_job(func=first_event, id=f'{record_id}_job1', trigger='date', run_date= datetime.now() + timedelta(seconds=5, hours=-2), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
            # job2 = scheduler.add_job(func=second_event, id=f'{record_id}_job2', trigger='date', run_date= datetime.now() + timedelta(seconds=10, hours=-2), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
            # job1 = 11
            # job2 = 11

            teacher = db.teachers_base.find_one({'_id':teacher_id})
            token = json.loads(teacher['token'])
            teachers_time_zone = int(teacher['timezone'])
            credentials = Credentials(token=token['token'],refresh_token=token['refresh_token'],client_id=token['client_id'],client_secret=token['client_secret'], scopes=token['scopes'],token_uri=token['token_uri'], expiry=token['expiry'])
            credentials.refresh(Request())            
            db.teachers_base.update_one({"_id": teacher_id}, {"$set": {'token': credentials.to_json()}})

            
            teachers_time_start = timestart + timedelta(hours=teachers_time_zone)
            teachers_time_end = teachers_time_start + timedelta(minutes=duration)
            gc = GoogleCalendar(credentials=credentials)
            try:
                event = gc.get_event(old_record['google_event_id'])
                event.start = teachers_time_start
                event.end = teachers_time_end
                gc.update_event(event)
            except: None
            
            db.records_base.update_one({'_id':int(record['_id'])},{ "$set": {
                                                    'template_id': template_id,
                                                    'teacher_id': teacher_id,
                                                    'student_id': student_id,
                                                    'subject': subject,
                                                    'date': date,
                                                    'time': time,
                                                    'timestart': timestart,
                                                    'full_date': full_date,
                                                    'duration': duration,
                                                    'price': price,
                                                    'teachers_fee': teachers_fee,
                                                    'status_record': status_record,
                                                    'status_payment': status_payment,
                                                    'status_payment_to_teacher': status_payment_to_teacher,
                                                    'job1': job1,
                                                    'job2': job2,
                                                }})
        if template_id != 'None' and template_id != '' and template_id != None:
            template = {
                'teacher_id': teacher_id,
                'student_id': student_id,
                'subject' : subject,
                'weekday': timestart.weekday(),
                'time': time,
                'duration': duration,
                'price': price,
                'teachers_fee': teachers_fee,
            }
            db.records_templates_base.update_one({'_id':template_id},{ "$set": template})

        if teacher_id_page==0 and shift==0:
            return redirect('/records')
        else:
            return redirect(f'/timetable?teacher_id={teacher_id_page}&shift={shift}')

    except:
        logger('error', message = traceback.format_exc())

# TIMETABLE
@routers_app.route('/timetable/', methods=['GET'])
def timetable_main():
    if 'username' not in session:
        return redirect('/login')
    
    # records_data = list(records_base.find({}))

    shift = request.args.get('shift', default = 0, type = int)
    teacher_id = request.args.get('teacher_id', default = 23454, type = int)

    print(teacher_id, shift)

    teachers_data = list(db.teachers_base.find({}))
    clients_data = list(db.clients_base.find({}))

    # teacher_id = 52342
    teacher_data = db.teachers_base.find_one({'_id':teacher_id})

    teachers_fullname = teacher_data['fullname']
    
    now = datetime.now() - timedelta(hours=2)
    monday_date = now - timedelta(days=now.weekday(), weeks=-shift, hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)

    teachers_week = []
    date_weekdays=[]

    for weekday_id in range(7):
        full_date = monday_date+timedelta(days=weekday_id)
        list_records=[]
        for record in list(db.records_base.find({'full_date': full_date, 'teacher_id':teacher_id})):
            if record['status_record'] == 'Запись отменена': continue
            client = db.clients_base.find_one({'_id':record['student_id']})
            time_end = record['timestart'] + timedelta(minutes=record['duration'])
            time_end = f'{time_end.hour}:{get_beauty_minutes(time_end.minute)}'

            if client == None: 
                clients_fullname = 'Not found'
                grade = 'Not found'
            else:
                clients_fullname = client['fullname']
                grade = client['grade']

            record.update({'students_fullname':clients_fullname, 'grade':grade, "time_end":time_end, 'teachers_fullname': teachers_fullname})
            list_records.append(record)
        teachers_week.append(list_records)
        month_date = str(full_date.month)
        if len(month_date)==1: month_date='0'+month_date
        date_weekdays.append([str(full_date.year),month_date,str(full_date.day)])

    return render_template('timetable_base.html', teachers_data=teachers_data, teacher_id=teacher_id, clients_data=clients_data, subjects=db.subjects, date_weekdays=date_weekdays, teachers_week=teachers_week, teachers_fullname=teachers_fullname, work_schedule=teacher_data['work_schedule'], shift=shift)


@routers_app.route('/salary_calculation/', methods=['GET'])
def salary_calculation():

    teacher_id = request.args.get('teacher_id', default = 0, type = int)
    records = list(db.records_base.find({'timestart': {'$lt': datetime.now()}, 'teacher_id':int(teacher_id), 'status_payment_to_teacher':'Не оплачено'}))

    teacher_fullname = db.teachers_base.find_one({'_id':teacher_id})['fullname']
    for record in records:
        student_fullname = db.clients_base.find_one({'_id': record['student_id']})['fullname']

        record.pop('template_id'); record.pop('teacher_id'); record.pop('student_id'); record.pop('timestart'); record.pop('creation_time'); record.pop('full_date'); record.pop('duration'); record.pop('meeting_link_for_student'); record.pop('meeting_link_for_teacher'); record.pop('link_to_record'); record.pop('job1'); record.pop('job2'); record.pop('canceled'); record.pop('google_event_id'); record.pop('price') 

        record.update({'teacher_fullname':teacher_fullname, 'student_fullname': student_fullname})

    return records

@routers_app.route('/salary_calculation/pay_teacher', methods=['GET'])
def salary_calculation_pay_teacher():
    record_ids = request.args.get('record_ids', default = '', type = str)[:-1].split(' ')

    for record_id in record_ids:
        db.records_base.update_one({'_id':int(record_id)},{ "$set": {'status_payment_to_teacher':'Оплачено'}})

    # logger('error', message = str(error) + '\n' + traceback.format_exc())
    
    # do_event(type='Покупка абонемента', client_id=transaction['client_id'], description=transaction['description'], amount=transaction['amount'], transaction_id=transaction['_id'])

    return {'status':'ok'}


# @routers_app.route('/statistic/', methods=['GET'])
# def statistic():


@routers_app.route('/settings/', methods=['GET'])
def settings():
    if 'username' not in session:
        return redirect('/login')
    
    return render_template('settings.html')



@routers_app.route('/transactions/', methods=['GET'])
def transactions():
    if 'username' not in session:
        return redirect('/login')
    
    transactions_data = list(db.transactions_base.find({}))
    for transaction in transactions_data:
        transaction['creation_time'] = str(transaction['creation_time']).split('.')[:1][0]

    return render_template('transactions.html', transactions_data=reversed(transactions_data))




@routers_app.route('/events/', methods=['GET'])
def events():
    if 'username' not in session:
        return redirect('/login')
    
    return render_template('events.html')




@routers_app.route('/statistic/', methods=['GET'])
def statistic():
    if 'username' not in session:
        return redirect('/login')
    now = datetime.now()

    statistic = {}
    records = db.records_base.find({'status_record':{'$ne':'Запись отменена'}})

    statistic['all'] = statistic_counter(records)

    months = {}
    for i in range(-4,1):
        month = (now + relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        records = db.records_base.find({'status_record':{'$ne':'Запись отменена'}, 'timestart': {'$gte': month, '$lt': (month + relativedelta(months=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)}})

        
        months[month.strftime('%B')] = statistic_counter(records)

    
    statistic['months'] = dict(reversed(months.items())) 
    return render_template('statistic.html', statistic=statistic)