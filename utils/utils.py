import random
import time
import hashlib
import json
import requests
import traceback
from nptime import nptime

from flask import render_template_string



from google.oauth2.credentials import Credentials
from gcsa.google_calendar import GoogleCalendar
from gcsa.conference import ConferenceSolutionCreateRequest, SolutionType
from gcsa.reminders import EmailReminder, PopupReminder
from google.auth.transport.requests import Request
from gcsa.event import Event

from datetime import datetime, timedelta

import sys
import os

# root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(root_path)
# print(root_path)

import config
from utils.database import db
from utils.logger import logger
from utils.scheduler import scheduler



def generate_id():
    timestamp = int(time.time())
    random_seq = random.randint(100, 999) 
    id = int(str(timestamp) + str(random_seq).zfill(4))
    return id

def get_subject_in(subject):
    if subject == 'Математика': return 'Математике'
    elif subject == 'Русский язык': return 'Русскому языку'
    elif subject == 'Химия': return 'Химии'
    elif subject == 'Биология': return 'Биологии'
    elif subject == 'Литература': return 'Литературе'
    elif subject == 'Информатика': return 'Информатике'
    elif subject == 'Физика': return 'Физике'
    elif subject == 'Обществознание': return 'Обществознанию'
    elif subject == 'Китайский язык': return 'Китайскому языку'
    elif subject == 'Английский язык': return 'Английскому языку'
    else: return 'Новому предмету'
        
def get_beauty_minutes(minutes):
    if len(str(minutes)) == 1: return f'0{minutes}'
    else: return str(minutes)


def add_hashtoken_and_dumps(data):
    token_data = data.copy()
    token_data.pop('Shops', None)
    token_data.pop('Receipt', None)
    token_data.pop('DATA', None)
    token_data.update({"Password":config.TERMINAL_PASS})
    tokenhash = ''
    print(token_data)
    for i in list(dict(sorted(token_data.items())).values()): tokenhash+=str(i)
    print(tokenhash)
    data.update({'Token':hashlib.sha256(str.encode(tokenhash)).hexdigest()})
    return json.dumps(data)


def create_description_for_record_pay(records):
    subjects = {}
    for record in records:
        if subjects.get(record['subject']) == None:
            subjects[record['subject']] = 1
        else:
            subjects[record['subject']] += 1
    
    text = 'Оплата урока по '
    for subject in subjects:
        text += get_subject_in(subject) + ', ' if  subjects[subject] == 1 else get_subject_in(subject) +  f' (x{subjects[subject]}), '
    if len(records) != 1: text = text.replace('урока', 'уроков')  

    return text[:-2]


def lesson_payment(records):
    transaction = {'_id':generate_id(), 'type':'Оплата урока', 'client_id': records[0]['student_id'], 'record_id': [], 'creation_time':datetime.now(), 'amount':0, 'description': create_description_for_record_pay(records), 'status': 'Ожидание оплаты'}

    for record in records:
        subject = record['subject']

        transaction['record_id'].append(record['_id'])
        transaction['amount'] += record['price']

        
    uri = "https://securepay.tinkoff.ru/v2/Init/"
    headers = {"Content-Type" : "application/json","Authorization" : "Bearer t.olv4VwHuxsclbHrO8eYAjZm9V7eEFvTVboltLHsPSNwlwr7Gsd4zJEP5_NOXJSpWS1a5GHEimipWK3j4qxl0WA"}
    #INIT PAY
    data = {"TerminalKey": config.TERMINAL_KEY, "Amount":transaction['amount']*100, "OrderId":transaction['_id'], "Description":transaction['description'],"NotificationURL":  config.NotificationURL, # "DATA": {'type':'Оплата одного урока'}
    }
    response = json.loads(requests.post(uri, headers=headers, data=add_hashtoken_and_dumps(data), timeout=100).text)  
    if response['Success'] != True: return 'Fail'
    payment_id = int(response['PaymentId'])
    # GET QR
    uri = "https://securepay.tinkoff.ru/v2/GetQr"
    headers = {"Content-Type" : "application/json","Authorization" : "Bearer t.olv4VwHuxsclbHrO8eYAjZm9V7eEFvTVboltLHsPSNwlwr7Gsd4zJEP5_NOXJSpWS1a5GHEimipWK3j4qxl0WA"}
    data = {"TerminalKey": config.TERMINAL_KEY, 'PaymentId' : payment_id}
    response = json.loads(requests.post(uri, headers=headers, data=add_hashtoken_and_dumps(data), timeout=100).text)
    logger('info', message = response)
    payment_link = response['Data']

    transaction.update({'payment_id':payment_id, 'payment_link': payment_link})

    link = 'https://a3artschool.su/pay/' + str(transaction['_id'])
    db.transactions_base.insert_one(transaction)
    return link


def abonement_payment(subject, price, client_id, tg_id):
    transaction = {'_id':generate_id(), 'type':'Оплата абонемента', 'client_id': client_id, 'subject': subject, 'creation_time':datetime.now(), 'amount':price, 'description':f'Оплата абонемента {subject} (x10)', 'status': 'Ожидание оплаты', 'tg_id': tg_id}
    
    uri = "https://securepay.tinkoff.ru/v2/Init/"
    headers = {"Content-Type" : "application/json","Authorization" : "Bearer t.olv4VwHuxsclbHrO8eYAjZm9V7eEFvTVboltLHsPSNwlwr7Gsd4zJEP5_NOXJSpWS1a5GHEimipWK3j4qxl0WA"}
    #INIT PAY
    data = {"TerminalKey":config.TERMINAL_KEY, "Amount":transaction['amount']*100, "OrderId":transaction['_id'], "Description":transaction['description'],"NotificationURL": config.NotificationURL, # "DATA": {'type':'Оплата одного урока'}
    }
    response = json.loads(requests.post(uri, headers=headers, data=add_hashtoken_and_dumps(data), timeout=100).text)  
    if response['Success'] != True: return 'Fail'
    payment_id = int(response['PaymentId'])
    print(payment_id)
    # GET QR
    uri = "https://securepay.tinkoff.ru/v2/GetQr"
    headers = {"Content-Type" : "application/json","Authorization" : "Bearer t.olv4VwHuxsclbHrO8eYAjZm9V7eEFvTVboltLHsPSNwlwr7Gsd4zJEP5_NOXJSpWS1a5GHEimipWK3j4qxl0WA"}
    data = {"TerminalKey": config.TERMINAL_KEY, 'PaymentId' : payment_id}
    payment_link = json.loads(requests.post(uri, headers=headers, data=add_hashtoken_and_dumps(data), timeout=100).text)['Data']

    transaction.update({'payment_id':payment_id, 'payment_link': payment_link})

    link = 'https://a3artschool.su/pay/' + str(transaction['_id'])
    db.transactions_base.insert_one(transaction)
    return link


def job_every_week():
    templates = db.records_templates_base.find({})
    now = datetime.now()
    monday_date = datetime.now() - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)

    for template in templates:
        template_id = template['_id']
        create_records_by_template(template_id, [monday_date + timedelta(weeks=2)])


def create_records_by_template(template_id,weeks):
    template = db.records_templates_base.find_one({'_id':template_id})

    teacher_id = template['teacher_id']
    student_id = template['student_id']
    subject = template['subject']
    weekday = template['weekday']
    time = template['time']
    duration = template['duration']
    price = template['price']
    teachers_fee = template['teachers_fee']

    client = db.clients_base.find_one({'_id':student_id})

    for monday_date in weeks:
        record_id = random.randint(10000000,99999999)
        
        timestart = monday_date + timedelta(days=weekday, hours=int(time.split(':')[0]), minutes=int(time.split(':')[1]))
        full_date = monday_date + timedelta(days=weekday)
        date = str(full_date.year)+'-'+get_beauty_minutes(full_date.month)+'-'+get_beauty_minutes(full_date.day)

        status_record = 'В ожидании клиента'
        status_payment = 'Не оплачен'
        status_payment_to_teacher = 'Не оплачено'
        # JOBS
        # clients_timezone = int(client['timezone'])

        job1 = scheduler.add_job(func=first_event, trigger='date', run_date= timestart + timedelta(hours=-6), args=[record_id], id=f'{record_id}_job1', jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
        job2 = scheduler.add_job(func=second_event, trigger='date', run_date= timestart + timedelta(minutes=duration), args=[record_id], id=f'{record_id}_job2', jobstore='mongo', replace_existing=True, misfire_grace_time=300).id

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

def statistic_counter(records):
    now = datetime.now()
    statistic_one = {'all_counts': 0, 'all_cost': 0, 'all_cost_potential': 0, 'subject_counts': {}, 'all_expenses': 0, 'all_expenses_potential': 0, 'profit': 0, 'profit_potential': 0, 'no_paid': 0, 'no_paid_overdue': 0}
    for record in records:
        if record['duration'] != 30:
            if record['status_payment'] != 'Не оплачен'  or record['status_record'] == 'Клиент пришел':
                statistic_one['all_counts'] += 1
                statistic_one['subject_counts'][record['subject']] = statistic_one['subject_counts'].get(record['subject'], 0) + 1
                
            if record['status_payment'] != 'Не оплачен':
                statistic_one['all_cost'] += record['price']
            statistic_one['all_cost_potential'] += record['price']

            if record['status_payment'] == 'Не оплачен':
                statistic_one['no_paid'] += 1
                if record['timestart'] < now:
                    statistic_one['no_paid_overdue'] += 1

        
            if record['status_payment_to_teacher'] == 'Оплачено':
                statistic_one['all_expenses'] += record['teachers_fee']
            statistic_one['all_expenses_potential'] += record['teachers_fee']

    
    statistic_one['profit'] = statistic_one['all_cost'] - statistic_one['all_expenses']
    statistic_one['profit_potential'] = statistic_one['all_cost_potential'] - statistic_one['all_expenses_potential']

    return statistic_one





def get_top(time):
    return int(time.split(':')[0])*60+int(time.split(':')[1])+14

def get_abonement(abonements, abonement):
    return abonements[abonement]

def get_intervals(weekday, teacher_id):
    weekday = int(weekday)
    teacher_id = int(teacher_id)
    working_hours = db.teachers_base.find_one({'_id': teacher_id})['work_schedule']['working_times'][weekday]
    working_hours = [nptime(int(time.split(':')[0]),int(time.split(':')[1])) for time in working_hours]
    intervals = ''
    times = []
    step = 0
    for i in range(96):
        times.append(nptime(0,0)+timedelta(minutes=step))
        step += 15
    interval = ''
    for time in times:
        if time in working_hours:
            if time == nptime(0,0) or time-timedelta(minutes=15) not in working_hours:
                if len(str(time.minute))==1: interval += f'{time.hour}:{time.minute}0'
                else: interval += f'{time.hour}:{time.minute}'
            elif time == nptime(23,45) or time+timedelta(minutes=15) not in working_hours:
                if len(str(time.minute))==1: interval += f'-{time.hour}:{time.minute}0'
                else: interval += f'-{time.hour}:{time.minute}'
                intervals += '_'+interval
                interval = ''
        else:
            continue
    return intervals[1:] 





def get_is_free_day(teacher_id, date):
    date = date[0]+'.'+date[1]+'.'+date[2]
    if date.split('.')[1][0] == '0' : date = date.split('.')[0]+'.'+date.split('.')[1][1:]+'.'+date.split('.')[2]
    if date in db.teachers_base.find_one({'_id': int(teacher_id)})['work_schedule']['free_days']: return True
    else: return False

def get_is_time_in_schedule(work_schedule, weekday, hour, minutes):
    if f'{hour}:{minutes}' in work_schedule['working_times'][int(weekday)]:
        return True
    else:
        return False
    
def get_isnot_free_day_timetable(work_schedule,year,month,day):
    if month[0] == '0' : date = f'{year}.{month[1]}.{day}'
    else: date = f'{year}.{month}.{day}'
    if date in work_schedule['free_days']:
        return False
    else:
        return True
    

def get_teachers_by_subject(subject):
    # teachers_by_subject = list(teachers_base.find({'spec': { "$in" : [subject] }}))
    # teachers_by_subject.append()
    return list(db.teachers_base.find({'spec': { "$in" : [subject] }}))

def get_studied_subject(studied_subjects, studied_subject):
    return studied_subjects[studied_subject]

def get_stripe(date):
    now = datetime.now()
    print(date, now)
    print(datetime(int(date[0]),int(date[1]),int(date[2])).date() == now.date())
    if datetime(int(date[0]),int(date[1]),int(date[2])).date() == now.date():
        return f'<div style="background-color: red; position: absolute; width: 100%; height: 6px; top: { now.hour*60+now.minute+12 }px; z-index:10; opacity: 0.98; border-radius: 7px;" ></div>'
    else:
        return ''




def first_event(record_id):
    try:
        record_id = int(record_id)  
        record = db.records_base.find_one({'_id':record_id})
        status_record = record.get('status_record','Запись отменена')
        if status_record != 'Запись отменена' or record == None:
            student = db.clients_base.find_one({'_id':record['student_id']}) 
            user_ids = student['tg_ids']
            subject = record['subject']
            students_timezone = student['timezone']
            timestart_for_student = record['timestart'] + timedelta(hours=int(students_timezone))
            duration = record['duration']
            abonement = int(student['abonements'].get(subject, 0))
            meeting_link_for_student = record['meeting_link_for_student']
            payment_link = ''
            if abonement == 1 or (abonement == 2 and duration == 120):
                text = db.texts['Клиент c заканчивающимся абонементом'].format(hour=timestart_for_student.hour, minute=get_beauty_minutes(timestart_for_student.minute), subject=get_subject_in(subject))

            elif abonement > 0 or duration == 30:
                text = db.texts['Клиент с абонементом'].format(hour=timestart_for_student.hour, minute=get_beauty_minutes(timestart_for_student.minute), subject=get_subject_in(subject))
            else:
                if record['status_payment'] == 'Не оплачен':
                    payment_link = lesson_payment([record])
                    text = db.texts['Клиент без абонемента'].format(hour=timestart_for_student.hour, minute=get_beauty_minutes(timestart_for_student.minute), subject=get_subject_in(subject))
                else:
                    text = db.texts['Клиент без абонемента'].format(hour=timestart_for_student.hour, minute=get_beauty_minutes(timestart_for_student.minute), subject=get_subject_in(subject))

            
            for user_id in user_ids:
                requests.get('http://127.0.0.1:5055/send_message', timeout=100, params={'user_id':user_id,'text':text, 'meeting_link':meeting_link_for_student, 'payment_link': payment_link})

            for user_id in config.administrator_ids:
                requests.get('http://127.0.0.1:5055/send_message', timeout=100, params={'user_id':user_id,'text':text, 'meeting_link':meeting_link_for_student, 'payment_link': payment_link})

    except:
        logger('error', message = traceback.format_exc())
        


def second_event(record_id):
    try:
        record_id = int(record_id)  
        record = db.records_base.find_one({'_id':record_id})
        status_record = record.get('status_record','Запись отменена')
        if status_record != 'Запись отменена' or record == None:
            student = db.clients_base.find_one({'_id':record['student_id']}) 
            user_ids = student['tg_ids']
            subject = record['subject']
            duration = record['duration']
            abonement = int(student['abonements'].get(subject,'0'))
            status_payment = record['status_payment']

            if status_payment == 'Не оплачен' and duration != 30:
                if abonement > 0:
                    factor = duration // 60
                    abonement -= factor
                    status_payment = 'Оплачено абонементом'
                    db.records_base.update_one({'_id':record_id},{ "$set": { 'status_payment': status_payment}})
                    db.clients_base.update_one({'_id':student['_id']},{ "$set": { f'abonements.{subject}': abonement}})

                    if abonement <= 0:
                        # абонемент закончился
                        text = 'Урок окончен!\nАбонемент закончился.'
                    # все оплачено, на абонементе осталось столько уроков
                    text = f'Урок окончен!\nОстаток уроков на балансе абонемента: {abonement}'
                else:
                    # не оплачено напомнить
                    text = 'Урок окончен!\nНе забудьте оплатить урок.'
            else:
                # все оплачено, подзороваться
                if abonement > 0:
                    text = f'Урок окончен!\nОстаток уроков на балансе абонемента: {abonement}'
                else:
                    text = 'Урок окончен!'

            for user_id in user_ids:
                requests.get('http://127.0.0.1:5055/send_message', timeout=100, params={'user_id':user_id,'text':text})

            for user_id in config.administrator_ids:
                requests.get('http://127.0.0.1:5055/send_message', timeout=100, params={'user_id':user_id,'text':text})

    except:
        logger('error', message = traceback.format_exc())

