from aiogram import types
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup as RKM, InlineKeyboardMarkup as IKM, KeyboardButton as KB, InlineKeyboardButton as IKB

from aiogram import Router, F
from aiogram import enums

from aiogram.filters import Command, CommandStart

import traceback

from datetime import datetime, timedelta, timezone
from aiogram.fsm.context import FSMContext

from utils.database import db

import config
from utils.utils import *
from utils.logger import logger
from aiogram import Bot



class States(StatesGroup):
    NEWSLETTER = State()
    TEXT_TO_NONAME = State()

    BUY_FOR_ONE_FROM_FAMILY = State()
    CHOISE_ABONEMENT = State()

    CHOISE_BANK = State()

    GO_STARTBOT = State()
    CHOISE_FULLNAME = State()
    ONE_FULLNAME = State()
    TWO_FULLNAME = State()
    SECOND_FULLNAME = State()
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

    

router = Router()


# base_keyboard = ["Следующий урок","Купить абонемент", "Баланс"]
# callbakes = CallbackData('callback','action','value')




# @dp.message_handler(text=['Купить абонемент', '/buy_abonement])
@router.message(F.text.lower() == '/buy_abonement')
async def btn_buy_abonement(msg: types.Message, state: FSMContext):
    user_id = str(msg.from_user.id)
    # state = await state.get_state()
    try:

        clients = list(db.clients_base.find({'tg_ids': { "$in" : [user_id] }}))

                
        if len(clients) != 1:
            clients_by_user_id = {}
            buttons = []
            for client in clients:
                students_name = client['fullname'].split(' ')[1]
                # name_for_crm = item['full_name'].split(' ')[1]+item['full_name'].split(' ')[0]

                clients_by_user_id.update({students_name:client})
                buttons.append(students_name)
                
            keyboard = RKM(keyboard = buttons,resize_keyboard=True)

            await state.update_data(clients_by_user_id=clients_by_user_id)
            await msg.answer('Выберите ребенка, которому хотите купить абонемент', reply_markup=keyboard)

            await state.set_state(States.BUY_FOR_ONE_FROM_FAMILY)
        else:
            client = clients[0]


            studied_subjects = client.get('studied_subjects', {})

            if studied_subjects == {}:
                await msg.answer('У вас пока что нет изучаемых предметов и не назначен учитель, обратитесь к администратору', reply_markup=db.base_keyboard)
                await state.clear()
                return
            else:
                subject_plan = {}
                buttons = []
                for studied_subject in studied_subjects:
                    plan = db.teachers_base.find_one({'_id':studied_subjects[studied_subject]})['rank']
                    subject_plan[studied_subject] = plan
                    if plan == 'junior':
                        buttons.append([KB(text=f"Абонемент {studied_subject} (x10) - {db.subjects[studied_subject]['price-cost'][0]['price'][1]}₽")])
                    elif plan == 'middle':
                        buttons.append([KB(text=f"Абонемент {studied_subject} (x10) - {db.subjects[studied_subject]['price-cost'][1]['price'][1]}₽")])
                    elif plan == 'senior':
                        buttons.append([KB(text=f"Абонемент {studied_subject} (x10) - {db.subjects[studied_subject]['price-cost'][2]['price'][1]}₽")])

            await state.update_data(client=client, subject_plan=subject_plan)

            buttons.append([KB(text="Назад")])
            print(buttons)

            keyboard = RKM(keyboard= buttons, resize_keyboard=True)

            await msg.answer('Выберите абонемент', reply_markup=keyboard)
            await state.set_state(States.CHOISE_ABONEMENT)

    except:
        logger('error', message = traceback.format_exc())

# @dp.message_handler(state=States.BUY_FOR_ONE_FROM_FAMILY)
@router.message(States.BUY_FOR_ONE_FROM_FAMILY)
async def buy_for_one_from_family(msg: types.Message, state: FSMContext):
    user_id = str(msg.from_user.id)
    
    try:
        data = await state.get_data()
        client = data['clients_by_user_id'][msg.text]

        # await state.update_data(client_id=client['_id'])

        buttons = []

        studied_subjects = client.get('studied_subjects', {})

        if studied_subjects == {}:
            buttons.append([f"Купить абонемент"])
            await msg.answer('У вас пока что нет изучаемых предметов и не назначен учитель, обратитесь к администратору', reply_markup=keyboard)
            await state.clear()
            return
        else:
            subject_plan = {}
            for studied_subject in studied_subjects:
                plan = db.teachers_base.find_one({'_id':studied_subjects[studied_subject]})['rank']
                subject_plan[studied_subject] = plan
                if plan == 'junior':
                    buttons.append([f"Абонемент {studied_subject} (x10) - {db.subjects[studied_subject]['price-cost'][0]['price'][1]}₽"])
                elif plan == 'middle':
                    buttons.append([f"Абонемент {studied_subject} (x10) - {db.subjects[studied_subject]['price-cost'][1]['price'][1]}₽"])
                elif plan == 'senior':
                    buttons.append([f"Абонемент {studied_subject} (x10) - {db.subjects[studied_subject]['price-cost'][2]['price'][1]}₽"])

        await state.update_data(client=client, subject_plan=subject_plan)

        buttons.append(["Назад"])
        keyboard = RKM(keyboard= buttons, resize_keyboard=True)
        await msg.answer('Выберите абонемент', reply_markup=keyboard)
        await state.set_state(States.CHOISE_ABONEMENT)


    except:
        logger('error', message = traceback.format_exc())



# @dp.message_handler(state=States.CHOISE_ABONEMENT)
@router.message(States.CHOISE_ABONEMENT)
async def choise_abonement(msg: types.Message, state: FSMContext):
    user_id = str(msg.from_user.id)

    if msg.text=='Назад': 
        await state.clear()
        await msg.answer("Покупка отменена", reply_markup=db.base_keyboard)
        return
    
    try:
    
        data = await state.get_data()
        client = data['client']
        subject_plan = data['subject_plan']

        # subject_context = msg.text.split(' - ')[0]
        for subject in db.subjects:
            if msg.text.find(subject) != -1:
                plan = subject_plan[subject]
                if plan == 'junior':
                    price = db.subjects[subject]['price-cost'][0]['price'][1]
                elif plan == 'middle':
                    price = db.subjects[subject]['price-cost'][1]['price'][1]
                elif plan == 'senior':
                    price = db.subjects[subject]['price-cost'][2]['price'][1]
                break
        
        link = abonement_payment(price = price, client_id=client['_id'],subject=subject,tg_id=user_id)



        await msg.answer(f'Ссылка для оплаты абонемента:\n{link}', reply_markup=db.base_keyboard)

        await state.clear()

    except:
        logger('error', message = traceback.format_exc())



# @dp.message_handler(text=["Баланс", "/balance"])
@router.message(F.text.lower() == "/balance")
async def balance(msg: types.Message):
    user_id = str(msg.from_user.id)
    try:

        clients = list(db.clients_base.find({'tg_ids': { "$in" : [user_id] }}))

        if len(clients) == 1: is_many = False
        else: is_many = True

        answer = ''
        for client in clients:
            if is_many == True:
                answer += '\n'+client['fullname'].split(' ')[1] + ':\n'
                caps = '    '
            else: caps = ''

            abonements_answer = ''
            for subject in client['abonements']:
                if client['abonements'][subject] not in ['0', 0]:
                    abonements_answer += f"{caps}{subject}: {client['abonements'][subject]}\n"

            if abonements_answer == '': abonements_answer = f'{caps}Абонемент не подключен\n'
            answer += abonements_answer
        
        await msg.answer(answer)

    except:
        logger('error', message = traceback.format_exc())



# @dp.message_handler(text=["Следующий урок", "/next_record"])
@router.message(F.text.lower() == "следующий урок")
async def next_record(msg: types.Message):
    user_id = str(msg.from_user.id)
    try:

        clients = list(db.clients_base.find({'tg_ids': { "$in" : [user_id] }}))

        if len(clients) == 1: is_many = False
        else: is_many = True

        now = datetime.now()

        answer = ''
        for client in clients:
            if is_many == True:
                answer += '\n'+client['fullname'].split(' ')[1] + ':\n'
                caps = '    '
            else: caps = ''

            # next_records = ''

            timezone = client['timezone']
            is_record = False
            for subject in db.subjects:
                records = list(db.records_base.find({'timestart': {'$gt': now}, 'student_id':client['_id'], 'subject':subject}).sort('timestart', 1))

                if records != []:
                    is_record = True
                    record = records[0]

                    students_time_start = record['timestart'] + timedelta(hours=int(timezone))

                    if len(str(students_time_start.minute)) == 1:
                        minute = '0'+str(students_time_start.minute)
                    else: minute = str(students_time_start.minute)
                    beautiful_time = str(students_time_start.hour)+':'+minute

                    date = str(students_time_start.day) + '.' + str(students_time_start.month)

                    if len(str(students_time_start.month)) == 1:
                        month = '0'+str(students_time_start.month)
                    else: month = str(students_time_start.month)

                    date = str(students_time_start.day) + '.' + month

                    if students_time_start.day - now.day == 0: recent = 'сегодня'
                    elif students_time_start.day - now.day == 1: recent = 'завтра'
                    elif students_time_start.day - now.day == 2: recent = 'послезавтра'
                    else: recent = False

                    weekday = students_time_start.weekday()
                    if weekday == 0 : weekday = 'в Понедельник'
                    if weekday == 1 : weekday = 'во Вторник'
                    if weekday == 2 : weekday = 'в Среду'
                    if weekday == 3 : weekday = 'в Четверг'
                    if weekday == 4 : weekday = 'в Пятницу'
                    if weekday == 5 : weekday = 'в Субботу'
                    if weekday == 6 : weekday = 'в Воскресенье'

                    # answer = 'Следующий урок по расписанию '
                    beuty_fulltime = ''
                    if recent==False:
                        beuty_fulltime += weekday + ', ' + date + ' в ' + beautiful_time 
                    else:
                        beuty_fulltime += recent + ' в ' + beautiful_time

                    answer += caps+'*·* '+subject+' '+beuty_fulltime+'\n'
            
            if is_record == False:
                answer += caps+'*·* Урок еще не запланирован\n'
                    
        await msg.answer(answer,parse_mode= enums.parse_mode.ParseMode.MARKDOWN)

    except:
        logger('error', message = traceback.format_exc())



# @dp.message_handler(text=["Долг"])
@router.message(F.text.lower() == "неоплаченные уроки")
async def pay_records(msg: types.Message):
    user_id = str(msg.from_user.id)

    now = datetime.now()

    try:

        clients = list(db.clients_base.find({'tg_ids': { "$in" : [user_id] }}))

        if len(clients) == 1: is_many = False
        else: is_many = True

        answer = ''
        for client in clients:
            if is_many == True:
                answer += '\n'+client['fullname'].split(' ')[1] + ':\n'
                caps = '    '
            else: caps = ''

            records = list(db.records_base.find({'status_payment': 'Не оплачен', 'timestart': {'$lt': now}, 'student_id':client['_id']}).sort('timestart', 1))
            if records == []:
                answer += caps+'Все оплачено'
                keyboard = None
            else:
                link = lesson_payment(records)
                answer += caps+'Неоплаченые уроки:\n'
                subjects = {}
                for record in records:
                    if subjects.get(record['subject']) == None:
                        subjects[record['subject']] = 1
                    else:
                        subjects[record['subject']] += 1

                for subject in subjects:
                    answer += caps+subject + ('' if subjects[subject] == 1 else f' (x{subjects[subject]})')
                
                keyboard = IKM(inline_keyboard=[[IKB(text='Оплатить', url=link)]])

        await msg.answer(answer,parse_mode=enums.parse_mode.ParseMode.MARKDOWN, reply_markup=keyboard)




    except:
        logger('error', message = traceback.format_exc())



# @dp.message_handler(text=["/default_bank"])
@router.message(F.text.lower() == "/default_bank")
async def choise_default_bank(msg: types.Message, state: FSMContext):
    user_id = str(msg.from_user.id)

    buttons = []
    for bank in db.bank_codes:
        buttons.append([KB(text=bank)])

    buttons.append([KB(text='Здесь нет моего банка')])

    keyboard = RKM(keyboard=buttons, resize_keyboard=True)
    await msg.answer( 'Выберите банк, который будет использоваться по умолчанию:', reply_markup=keyboard)

    await state.set_state(States.CHOISE_BANK)


# @dp.message_handler(state=States.CHOISE_BANK)
@router.message(States.CHOISE_BANK)
async def choise_default_bank2(msg: types.Message, state: FSMContext, bot: Bot):
    user_id = str(msg.from_user.id)
    username = msg.from_user.username


    if msg.text == 'Здесь нет моего банка':
        for administrators_id in config.administrator_ids:
            await bot.send_message(administrators_id, f'Пользователь id_tg: {user_id} @{username} заявил, что его банка нет в списке')
        
        await msg.answer( 'Приняли!\nВ течение 10 минут Вам напишет администратор.', reply_markup=db.base_keyboard)
        await state.clear()
        return

        

    clients = list(db.clients_base.find({'tg_ids': { "$in" : [user_id] }}))

    for client in clients:
        db.clients_base.update_one({'_id':client['_id']},{ "$set": { 'default_bank':  msg.text}})

    await msg.answer( 'Банк добавлен!\nТеперь все ссылки на оплату будут открываться при помощи этого банка', reply_markup=db.base_keyboard)
    await state.clear()



# @dp.message_handler(text=["Автооплата", "/autopay"])
# async def autopay(dp, msg: types.Message):
#     user_id = str(msg.from_user.id)

    

    