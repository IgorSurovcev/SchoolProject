
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

import config
from utils.utils import *
from utils.logger import logger
from utils.scheduler import scheduler

from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder 
from aiogram import Bot


from utils.database import db

# base_keyboard = ["Следующий урок","Купить абонемент", "Баланс"]
class callbakes(CallbackData, prefix='start'):
    action: str
    value: Optional[str]

class States(StatesGroup):
    NEWSLETTER = State()
    TEXT_TO_NONAME = State()

    BUY_FOR_ONE_FROM_FAMILY = State()
    CHOISE_ABONEMENT = State()

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

# @dp.message_handler(lambda message: message.text[:8] == 'https://')
# @dp.message_handler(text=['Отправить домашнее задание', 'Задать тест'])
@router.message(F.text[:8] == 'https://')
@router.message(F.text.in_(['Отправить домашнее задание', 'Задать тест']))
async def teacher_handler(msg: types.Message, state: FSMContext, bot: Bot):
    user_id = str(msg.from_user.id)
    try:
        teacher = db.teachers_base.find_one({'id_tg': { "$in" : [user_id] }})
        keyboard = []

        if teacher != None:
            if msg.text == 'Отправить домашнее задание':
                now = datetime.today() + timedelta(hours=3)
                records = list(db.records_base.find({
                    'timestart': {'$lt': now, '$gt': now - timedelta(hours=36)}, 
                    'teacher_id':teacher['_id'],
                    'status_record': {'$ne': 'Запись отменена'},
                    'got_hometask': {'$exists': False}
                }).sort('timestart', 1))

                interpretation_buttons = {}
                for record in records:
                    teachers_time_start = record['timestart'] + timedelta(hours=int(teacher['timezone']))
                    teachers_time_start_str = str(teachers_time_start.day)+'.'+str(teachers_time_start.month)+'.'+str(teachers_time_start.year)
                    students_name = db.clients_base.find_one({'_id':record['student_id']})['fullname'].split(' ')[1]
                    if len(str(teachers_time_start.minute)) == 1:
                        minute = '0'+str(teachers_time_start.minute)
                    else: minute = str(teachers_time_start.minute)
                    beautiful_time = str(teachers_time_start.hour)+':'+minute
                    answer = students_name+' '+teachers_time_start_str+' '+ beautiful_time
                    keyboard.append([KB(text=answer)])
                    interpretation_buttons.update({answer:record['_id']})

                keyboard.append([KB(text='Отмена')])
                await msg.answer('Выбери ученика по прошедшему уроку', reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
                await state.update_data(interpretation_buttons=interpretation_buttons)
                await state.set_state(States.CHOISE_STUDENT_FOR_HOMETASK)
            elif msg.text[:8] == 'https://':
                keyboard.append([KB(text="Отправить домашнее задание")])

                # now = datetime.today() + timedelta(hours=3)
                now = datetime.now()
                records = list(db.records_base.find({
                    'timestart': {'$lt': now - timedelta(minutes=10), '$gt': now - timedelta(hours=12)}, 
                    'teacher_id':teacher['_id'], 
                    'status_record': {'$ne': 'Запись отменена'}
                }).sort('timestart', -1)) 

                if records == []:
                    await msg.answer('У тебя сегодня не было уроков')
                    return
                
                record = records[0]
                
                if record['link_to_record'] != '':
                    await msg.answer('Прошлому ученику уже приходила ссылка', reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
                    return

                client = db.clients_base.find_one({'_id':record['student_id']})

                for client_user_id in client['tg_ids']:
                    try:
                        await bot.send_message(client_user_id, 'Ссылка на запись урока:\n'+msg.text)
                    except Exception as e:
                        print('error send link record',e, client_user_id)

                db.records_base.update_one({'_id':record['_id']},{ "$set": {'link_to_record': msg.text }})

                await msg.answer('Ссылка отправлена: '+client['fullname'].split(' ')[1], reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))

    except:
        logger('error', message = traceback.format_exc())

# @dp.message_handler(state=States.CHOISE_STUDENT_FOR_HOMETASK)
@router.message(States.CHOISE_STUDENT_FOR_HOMETASK)
async def choise_student_for_hometask(msg: types.Message, state: FSMContext):
    try:
        if msg.text=='Отмена': 
            await state.clear()
            keyboard = []
            keyboard.append([KB(text="Отправить домашнее задание")])
            await msg.answer("Отменено", reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
            return

        await state.update_data(choise_student_for_hometask=msg.text)
        keyboard = []
        keyboard.append([KB(text="Нет задания"), KB(text="Отмена")])
        await msg.answer('Пришли домашнее задание. Что отправишь, то и придет ученику (файл, изображение, текст, но не группа!)\nИли сообщи, что нет домашнего задания', reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
        await state.set_state(States.SEND_HOMETASK)

    except:
        logger('error', message = traceback.format_exc())

# @dp.message_handler(state=States.SEND_HOMETASK,content_types=types.ContentType.ANY)
@router.message(States.SEND_HOMETASK)
async def send_hometask(msg: types.Message, state: FSMContext, bot: Bot):
    user_id = str(msg.from_user.id)
    try:
        if msg.text=='Отмена': 
            await state.clear()
            keyboard = []
            keyboard.append([KB(text="Отправить домашнее задание")])
            await msg.answer("Отменено", reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
            return

        data = await state.get_data()
        record_id = data['interpretation_buttons'][data['choise_student_for_hometask']]

        if msg.text=='Нет задания': 
            db.records_base.update_one({'_id':record_id},{ "$set": {'got_hometask': True }})

            await state.clear()
            keyboard = []
            keyboard.append([KB(text="Отправить домашнее задание")])
            await msg.answer("Отменено", reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
            return

        record = db.records_base.find_one({'_id': record_id})

        ids = db.clients_base.find_one({'_id':record['student_id']})['tg_ids']
        for student_user_id in ids:
            try:
                time.sleep(0.1)
                await msg.copy_to(chat_id=student_user_id)
            except Exception as e:
                print('error send hometask',e, student_user_id)

        db.records_base.update_one({'_id':record_id},{ "$set": {'got_hometask': True }})
            
        await state.clear()
        keyboard = []
        keyboard.append([KB(text="Отправить домашнее задание")])
        await msg.answer('Домашнее задание было отправлено', reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))

    except:
        logger('error', message = traceback.format_exc())



# @dp.message_handler(text=['newsletter','Newsletter'])
async def newsletter(msg: types.Message, state: FSMContext, bot: Bot):
    user_id = str(msg.from_user.id)
    if user_id not in config.administrator_ids : return 
    
    keyboard = []
    keyboard.append([KB(text="/cancel")])
    await msg.answer('Пришли сообщение для рассылки. В точно таком же виде оно будет отправлено всем пользователям.', reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
    await state.set_state(States.NEWSLETTER)


# @dp.message_handler(state=States.NEWSLETTER,content_types=types.ContentType.ANY)
async def newsletter_2(msg: types.Message, state: FSMContext, bot: Bot):    
    keyboard = []
    keyboard.append([KB(text="Отправить домашнее задание")])

    if msg.text=='/cancel': 
        await state.clear()
        await msg.answer("Ввод сброшен, можешь расслабиться", reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
        return
    
    ids = set()    
    for client in db.clients_base.find():
        user_ids = client['tg_ids']
        for user_id in user_ids:
            if user_id != '': ids.add(user_id)

    # ids = set()  
    # ids.add('676352317')
 
    for user_id in ids:
        try:
            time.sleep(0.1)
            await msg.copy_to(chat_id=user_id, reply_markup=db.base_keyboard)

        except Exception as e:
            print('errore send letters',e, user_id)
    

    await msg.answer('Сообщение было разослано всем ученикам, кто нажал /start', reply_markup=RKM(keyboard=keyboard, resize_keyboard=True))
    
    await state.clear()