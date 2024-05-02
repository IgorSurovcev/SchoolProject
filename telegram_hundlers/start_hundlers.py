from aiogram import types
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup as RKM, InlineKeyboardMarkup as IKM, KeyboardButton as KB, InlineKeyboardButton as IKB

from aiogram import Router, F
from aiogram import enums
from aiogram.filters import Command, CommandStart

import json
import phonenumbers
import random

from datetime import datetime, timedelta, timezone, time as dtime

import time as stamp_time
from aiogram.fsm.context import FSMContext

from utils.database import db

import config
from utils.utils import *
from utils.logger import logger
from utils.scheduler import scheduler

from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder 
from aiogram import Bot
from utils.utils import first_event, second_event



router = Router()



class States(StatesGroup):
    NEWSLETTER = State()
    TEXT_TO_NONAME = State()

    BUY_FOR_ONE_FROM_FAMILY = State()
    CHOISE_ABONEMENT = State()

    GO_STARTBOT = State()
    CHOISE_FULLNAME = State()
    FULLNAME = State()

    # ONE_FULLNAME = State()
    # TWO_FULLNAME = State()
    # SECOND_FULLNAME = State()
    TIMEZONE = State()
    CONTACT = State()
    PROMO_CODE = State()
    SUBJECT = State()
    GRADE = State()
    DAY = State()
    TIME = State()

    TEACHER = State()
    SEND_HOMETASK = State()

    CHOISE_STUDENT_FOR_HOMETASK = State()

    CHOISE_STUDENT_FOR_TEST = State()
    CHOISE_TEST = State()
    STUDENTS_NUMBER_FOR_TEST = State()


class callbakes(CallbackData, prefix='start'):
    action: str
    value: Optional[str]

tz_1 = [['МСК-1','МСК+0','МСК+1'],['МСК+2','МСК+3','МСК+4'],['МСК+5','МСК+6','МСК+7'],['МСК+8','МСК+9','Другое']]
tz_2 = [['GMT+0', 'GMT+1','GMT+2'], ['GMT-1', 'GMT-2', 'GMT-3'], ['GMT-4', 'GMT-5', 'GMT-6'], ['GMT-7', 'GMT-8', 'GMT-9'], ['GMT-10','GMT-11','Назад']]

@router.message(States.FULLNAME)
async def get_fullname(msg: types.Message, state: FSMContext):
    user_id = str(msg.from_user.id)

    full_name = msg.text
    if len(full_name.split(' ')) != 3 and len(full_name.split(' ')) != 2:
        await msg.answer('Кажется, вы неправильно ввели ФИО, попробуйте еще раз')
        return
    
    await state.update_data(full_name=full_name)
    
    keyboard = []
    for row in tz_1:
        keyboard.append([IKB(text= row[0], callback_data=callbakes(action='get_timezone', value=row[0]).pack()),
                         IKB(text= row[1], callback_data=callbakes(action='get_timezone', value=row[1]).pack()),
                         IKB(text= row[2], callback_data=callbakes(action='get_timezone', value=row[2]).pack())])
        
    stamp_time.sleep(0.5)
    await msg.answer('Выберете свой часовой пояс относительно Москвы:', reply_markup=IKM(inline_keyboard=keyboard, resize_keyboard=True))

    await state.set_state(States.TIMEZONE)


# @dp.callback_query_handler(callbakes.filter(action='get_timezone'),state=States.TIMEZONE)
@router.callback_query(States.TIMEZONE, callbakes.filter(F.action == "get_timezone"))
async def get_timezone(query: types.CallbackQuery, callback_data: callbakes, state: FSMContext):       
    value = callback_data.value                  
    if value=='Другое':
        keyboard = []
        for row in tz_2:
            keyboard.append([IKB(text=row[0], callback_data=callbakes(action='get_timezone_2', value=row[0]).pack()),
                             IKB(text=row[1], callback_data=callbakes(action='get_timezone_2', value=row[1]).pack()),
                             IKB(text=row[2], callback_data=callbakes(action='get_timezone_2', value=row[2]).pack())])  
                  
        await query.message.edit_text('Выберете свой часовой пояс относительно Москвы:', reply_markup=IKM(inline_keyboard=keyboard, resize_keyboard=True))
        return
    
    await state.update_data(timezone=int(value[3:]))
    # await query.message.edit_text(text='Часовой пояс успешно введен', inline_message_id= str(query.message.message_id))
    await query.message.delete()
    keyboard = RKM(keyboard=[[KB(text='Ввести номер автоматически',request_contact=True)]], resize_keyboard=True)
    await query.message.answer('Остался только номер телефона и можно приступать к выбору времени.\nЕго можно ввести автоматически, нажав на кнопку ниже',reply_markup=keyboard)
    await state.set_state(States.CONTACT)


# @dp.callback_query_handler(callbakes.filter(action='get_timezone_2'),state=States.TIMEZONE)
@router.callback_query(States.TIMEZONE, callbakes.filter(F.action == "get_timezone_2"))
async def get_timezone_2(query: types.CallbackQuery, callback_data: dict, state: FSMContext):       
    value = callback_data.value
    if value=='Назад':
        keyboard = []
        for row in tz_1:
            keyboard.append([IKB(text= row[0], callback_data=callbakes(action='get_timezone', value=row[0]).pack()),
                             IKB(text= row[1], callback_data=callbakes(action='get_timezone', value=row[1]).pack()),
                             IKB(text= row[2], callback_data=callbakes(action='get_timezone', value=row[2]).pack())])        
        await query.message.edit_text('Выберите свой часовой пояс:', query.message.message_id, reply_markup=IKM(inline_keyboard=keyboard, resize_keyboard=True))
        
        return    
    await state.update_data(timezone=int(value[3:])-3)    
    # await query.message.edit_text(text='Часовой пояс успешно введен', inline_message_id= str(query.message.message_id))   
    await query.message.delete() 
    keyboard = RKM(keyboard=[[KB(text='Ввести номер автоматически', request_contact=True)]], resize_keyboard=True)
    stamp_time.sleep(0.5)
    await query.message.answer('Осталось ввести телефон (это очень нужно, чтоб убедиться, что вы настоящий человек)\nЕго можно ввести автоматически, нажав на кнопку ниже',reply_markup=keyboard)
    await state.set_state(States.CONTACT)





# @dp.message_handler(content_types=['contact'],state=States.CONTACT)
# @dp.message_handler(state=States.CONTACT)
# @router.message(States.CONTACT, F.type == 'contact')
@router.message(States.CONTACT)
async def contact(msg: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    # if data['timezone'] < 0 : timezone = str(data['timezone'])
    # elif data['timezone'] >= 0 : timezone = '+'+str(data['timezone'])

    if msg.contact == None:
        try:
            number_parse = phonenumbers.parse(msg.text)

            if not phonenumbers.is_valid_number(number_parse):
                stamp_time.sleep(0.5)
                await msg.answer('Кажется, Вы неправильно ввели номер. Попробуйте еще раз или позвольте ввести его автоматически')
                return
            number = '+'+str(number_parse.country_code) + str(number_parse.national_number)

        except:
            stamp_time.sleep(0.5)
            await msg.answer('Кажется, Вы неправильно ввели номер. Попробуйте еще раз или позвольте ввести его автоматически')
            return
        
    else:
        number = str(msg.contact.phone_number)
        if number[0] != '+': number = '+'+number


    if msg.from_user.username != None:
        username = '@'+str(msg.from_user.username) 
    else: username = None
    
    for administrators_id in config.administrator_ids:
        await bot.send_message(administrators_id, f'Пользователь c номером {number} и username {username} начал регистрацию')
 
    await state.update_data(number=number)
    await msg.answer('Номер введен успешно', reply_markup=types.ReplyKeyboardRemove())

    stamp_time.sleep(0.5)

    keyboard = []
    for grade in ['5 класс', '6 класс', '7 класс', '8 класс', '9 класс', '10 класс', '11 класс']:
        keyboard.append([IKB(text=grade, callback_data=callbakes(action='grade_choise', value=grade).pack())])
    await msg.answer('Какой у Вас класс?',reply_markup=IKM(inline_keyboard=keyboard, resize_keyboard=True))
    await state.set_state(States.GRADE)





# @dp.callback_query_handler(callbakes.filter(action='grade_choise'),state=States.GRADE)
@router.callback_query(States.GRADE, callbakes.filter(F.action == "grade_choise"))
async def grade_choise(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    data = await state.get_data()
    grade = callback_data.value

    await state.update_data(grade=grade)

    keyboard = []
    for subject in list(db.subjects.keys()):
        keyboard.append([IKB(text=subject, callback_data=callbakes(action='subject_choise', value=subject).pack())])
    
    stamp_time.sleep(0.5)
    await query.message.edit_text('Предмет:', reply_markup=IKM(inline_keyboard=keyboard, resize_keyboard=True))
    await state.set_state(States.SUBJECT)





# @dp.callback_query_handler(callbakes.filter(action='subject_choise'),state=States.SUBJECT)
@router.callback_query(States.SUBJECT, callbakes.filter(F.action == "subject_choise"))
async def subject_choise(query: types.CallbackQuery, callback_data: dict, state: FSMContext): 
    subject = callback_data.value
    await state.update_data(subject=subject)

    data = await state.get_data()

    subject = data['subject']
    timezone = int(data['timezone'])

    teacher = db.teachers_base.find_one({'_id': db.subjects[subject]['id_main_teachers'][0]})

    await state.update_data(teacher_id=teacher['_id'])

    work_schedule = teacher['work_schedule']

    start_date = datetime.combine((datetime.now() + timedelta(hours=timezone+3)).date() + timedelta(days=1), dtime())

    # build seven days
    seven_days = []
    plus_day = -1
    while len(seven_days) < 7 and plus_day <= 20:
        plus_day += 1
        date = start_date + timedelta(days=plus_day)
        weekday = date.weekday()

        if date.strftime("%Y.%#m.%#d") in work_schedule['free_days'] or work_schedule['working_times'][weekday] == []: continue

        times = work_schedule['working_times'][weekday]

        times.pop(-1)
        times.pop(-2)

        records = list(db.records_base.find({'timestart': {'$gte': date, '$lt': date + timedelta(days=1)}, 'teacher_id':teacher['_id'], 'status_record': {'$ne': 'Запись отменена'}}))

        times = [nptime(int(time.split(':')[0]),int(time.split(':')[1])) for time in times]

        for record in records:
            blocked_time = record['timestart'] - timedelta(minutes=15)
            while blocked_time <= record['timestart'] + timedelta(minutes=record['duration']):
                npblocked_time = nptime(blocked_time.hour, blocked_time.minute)
                if npblocked_time in times: times.remove(npblocked_time)
                
                blocked_time += timedelta(minutes=15)
                
        if set(times) == set([None]): continue  

        times = [time + timedelta(hours=timezone) for time in times]
        times.sort()


        if weekday == 0 : weekday = 'Понедельник'
        if weekday == 1 : weekday = 'Вторник'
        if weekday == 2 : weekday = 'Среда'
        if weekday == 3 : weekday = 'Четверг'
        if weekday == 4 : weekday = 'Пятница'
        if weekday == 5 : weekday = 'Суббота'
        if weekday == 6 : weekday = 'Воскресенье'
        
        if len(str(date.day)) == 1: days = '0'+str(date.day)
        else: days = str(date.day)
        beautiful_date = '('+days+'.'+str(date.month)+')'

        seven_days.append({'date':date,'times':times,'weekday':weekday + ' ' + beautiful_date})

        
    keyboard = []
    await state.update_data(seven_days=seven_days)

    print(seven_days)

    for day in seven_days:        
        keyboard.append([IKB(text=day['weekday'], callback_data=callbakes(action='weekday_choise', value=day['weekday']).pack())])

    stamp_time.sleep(0.5)
    await query.message.edit_text('Осталось подумать над временем пробного урока:', reply_markup=IKM(inline_keyboard=keyboard))
    await state.set_state(States.DAY)




# @dp.callback_query_handler(callbakes.filter(action='weekday_choise'),state=States.DAY)
@router.callback_query(States.DAY, callbakes.filter(F.action == "weekday_choise"))
async def weekday_choise(query: types.CallbackQuery, callback_data: dict, state: FSMContext): 
    weekday = callback_data.value
    await state.update_data(weekday=weekday)
    
    data = await state.get_data()
    seven_days = data['seven_days']
    
    for choised_day in seven_days:
        if choised_day['weekday'] == weekday: break
    await state.update_data(choised_day=choised_day)
    
    builder = InlineKeyboardBuilder()
    for time in choised_day['times']:
        if time == None: continue
        if len(str(time.minute)) == 1:
            minute = '0'+str(time.minute)
        else: minute = str(time.minute)
        beautiful_time = str(time.hour)+':'+minute
        builder.button(text= beautiful_time, callback_data=callbakes(action='time_choise', value=beautiful_time.replace(':','-')))
        
    builder.button(text='Назад', callback_data=callbakes(action='time_choise', value='Назад'))
    builder.adjust(4)
    stamp_time.sleep(0.5)
    await query.message.edit_text('Выберите время:', reply_markup=builder.as_markup())
    await state.set_state(States.TIME)
    
    
# @dp.callback_query_handler(callbakes.filter(action='time_choise'),state=States.TIME)
@router.callback_query(States.TIME, callbakes.filter(F.action == "time_choise"))
async def time_choise(query: types.CallbackQuery, callback_data: dict, state: FSMContext, bot: Bot):
    user_id = str(query.from_user.id)
    if query.from_user.username != None:
        username = '@'+str(query.from_user.username) 
    else: username = None
    
    data = await state.get_data()
    simple_time = callback_data.value.replace('-',':')
    seven_days = data['seven_days']
    # await state.update_data(value=value)
    if simple_time == 'Назад':
        keyboard = []
        for day in seven_days:        
            keyboard.append([IKB(text=day['weekday'], callback_data=callbakes(action='weekday_choise', value=day['weekday']).pack())])
            stamp_time.sleep(0.5)
        await query.message.edit_text('Выберите день:', reply_markup=keyboard)
        await state.set_state(States.DAY)
        return
    
    #get data
    data = await state.get_data()
    grade = data['grade']
    subject = data['subject']
    number = data['number']
    full_name = data['full_name']
    timezone = int(data['timezone'])
    teacher_id = data['teacher_id']
    weekday = data['weekday']
    choised_day = data['choised_day']
        
    timestart = choised_day['date'] + timedelta(hours=int(simple_time.split(':')[0])-timezone,minutes=int(simple_time.split(':')[1]))    
    print(choised_day, timestart)
    # timestart = datetime(choised_day['date'].year, choised_day['date'].month, choised_day['date'].day, ) timedelta(hours=int(simple_time.split(':')[0])-timezone,minutes=int(simple_time.split(':')[1])) 

    student_id = random.randint(1000000,9999999)
    phone = data['number']
    # mail = request.form['mail']
    fullname = data['full_name']
    # parents_fullname = request.form.get('parents_fullname', '')
    timezone = '+'+str(timezone) if timezone >= 0 else str(timezone)
    grade = data['grade']
    # parents_username_tg = request.form['parents_username_tg']
    students_username_tg = username
    tg_ids = [user_id]
    abonements = {subject: 0 for subject in db.subjects}
    studied_subjects = []
    tags = []
    info = ''

    db.clients_base.insert_one({
        '_id': student_id,
        'phone': phone,
        # 'mail': mail,
        'fullname' : fullname,
        # 'parents_fullname': parents_fullname,
        'timezone': timezone,
        'grade': grade,
        'students_username_tg': students_username_tg,
        'tg_ids': tg_ids,
        'abonements' : abonements,
        'studied_subjects': studied_subjects,
        'tags': tags,
        'info': info
    })



    record_id = random.randint(10000000,99999999)

    teacher_id = teacher_id
    student_id = student_id
    subject = subject

    date = str(timestart.year)+'-'+get_beauty_minutes(timestart.month)+'-'+get_beauty_minutes(timestart.day)
    # if len(request.form['date'].split('-')[2]) == 1: date = request.form['date'].split('-')[0] + request.form['date'].split('-')[1] + '0' + request.form['date'].split('-')[2]
    time = f'{timestart.hour}:{get_beauty_minutes(timestart.minute)}'
    full_date = datetime(int(date.split('-')[0]),int(date.split('-')[1]),int(date.split('-')[2]))
    duration = 30
    price = 0
    teachers_fee = 0

    status_record = 'В ожидании клиента'
    status_payment = 'Оплачено разово'
    status_payment_to_teacher = 'Оплачено'
    # JOBS
    job1 = scheduler.add_job(func=first_event, id=f'{record_id}_job1', trigger='date', run_date= timestart + timedelta(hours=-6), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id
    job2 = scheduler.add_job(func=second_event, id=f'{record_id}_job2', trigger='date', run_date= timestart + timedelta(minutes=duration), args=[record_id], jobstore='mongo', replace_existing=True, misfire_grace_time=300).id

    # GOOGLE CALENDAR AND MEETING
    teacher = db.teachers_base.find_one({'_id': teacher_id})

    if teacher.get('token') != None:
        try:
            token = json.loads(teacher['token'])

            credentials = Credentials(token=token['token'], refresh_token=token['refresh_token'], client_id=token['client_id'], client_secret=token['client_secret'], scopes=token['scopes'], token_uri=token['token_uri'], expiry=token['expiry'])
            credentials.refresh(Request())
            db.teachers_base.update_one({"_id": teacher_id}, {"$set": {'token': credentials.to_json()}}) # UPDATE TOKEN IN BASE

            gc = GoogleCalendar(credentials=credentials)
            conference_solution=ConferenceSolutionCreateRequest(solution_type=SolutionType.HANGOUTS_MEET)
        except:
            pass

    teachers_time_zone = int(teacher['timezone'])

    teachers_time_start = timestart + timedelta(hours=teachers_time_zone)
    teachers_time_end = teachers_time_start + timedelta(minutes=duration)

    event = Event(summary=fullname.split(' ')[1]+' || '+grade+' || '+subject, start=teachers_time_start, end=teachers_time_end, timezone = f'Etc/GMT{-3-teachers_time_zone}', reminders=PopupReminder(minutes_before_start=25), conference_solution=conference_solution, color_id=7, event_id = random.randint(10000000,19999999)) # description = location)
    gc.add_event(event)
    google_event_id = event.event_id
    event = gc.get_event(google_event_id)
    conference_id = event.conference_solution.conference_id

    meeting_link_for_student = f'https://{config.HOSTNAME}/meeting_link/'+str(conference_id)
    meeting_link_for_teacher = 'https://meet.google.com/'+str(conference_id)
    link_to_record = ''

    template_id = 'None'

    print({
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
        'status_record': status_record,
        'status_payment': status_payment,
        'status_payment_to_teacher': status_payment_to_teacher,
        'meeting_link_for_student': meeting_link_for_student,
        'meeting_link_for_teacher': meeting_link_for_teacher,
        'link_to_record': link_to_record,
        'job1': job1,
        'job2': job2,
        'canceled': False,
        'google_event_id': google_event_id
    })

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
        'status_record': status_record,
        'status_payment': status_payment,
        'status_payment_to_teacher': status_payment_to_teacher,
        'meeting_link_for_student': meeting_link_for_student,
        'meeting_link_for_teacher': meeting_link_for_teacher,
        'link_to_record': link_to_record,
        'job1': job1,
        'job2': job2,
        'canceled': False,
        'google_event_id': google_event_id
    })


        
    if weekday.split(' ')[0] == 'Понедельник': weekday = 'в Понедельник ' + weekday.split(' ')[1]
    if weekday.split(' ')[0] == 'Вторник': weekday = 'во Вторник ' + weekday.split(' ')[1]
    if weekday.split(' ')[0] == 'Среда': weekday = 'в Среду ' + weekday.split(' ')[1]
    if weekday.split(' ')[0] == 'Четверг': weekday = 'в Четверг ' + weekday.split(' ')[1]
    if weekday.split(' ')[0] == 'Пятница': weekday = 'в Пятницу ' + weekday.split(' ')[1]
    if weekday.split(' ')[0] == 'Суббота': weekday = 'в Субботу ' + weekday.split(' ')[1]
    if weekday.split(' ')[0] == 'Воскресенье': weekday = 'в Воскресенье ' + weekday.split(' ')[1]


    if len(str(timestart.minute))==1: minutes='0'+str(timestart.minute)
    else: minutes = str(timestart.minute)
    for administrators_id in config.administrator_ids:
        await bot.send_message(administrators_id, f'Пользователь {full_name} c номером {number} и username {username} закончил регистрацию\nЗаписан {weekday} на {timestart.hour}:{minutes} на пробный урок по предмету {subject}') 

    await query.message.delete()
    # await bot.edit_message_text('Урок запланирован. 🎉',query.from_user.id, query.message.message_id)

    # await bot.send_photo(user_id, photo=open('image3.png',"rb"),caption=blanks['welcome'], reply_markup=keyboard)
    stamp_time.sleep(0.5)
    await query.message.answer('Урок запланирован. 🎉 \nДалеко этого бота не откладывайте, он Вам еще понадобится.\nЗдесь же Вам придет за 6 часов до начала урока напоминание и ссылка для подключения к уроку', reply_markup=db.base_keyboard)
    
    await state.clear()