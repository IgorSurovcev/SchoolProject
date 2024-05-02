
import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.methods.delete_webhook import DeleteWebhook

from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext


import traceback
from utils.database import db
import config
from utils.utils import *
from utils.logger import logger

from aiogram.types import ReplyKeyboardMarkup as RKM, InlineKeyboardMarkup as IKM, KeyboardButton as KB

from telegram_hundlers.commands_hundlers import router as commands_router
from telegram_hundlers.start_hundlers import router as start_router
from telegram_hundlers.teachers_hundlers import router as teachers_router

# from telegram_hundlers import teachers_hundlers, commands_hundlers, start_hundlers


API_TOKEN = '5637578020:AAG9UtnefJHHZXHzs4v_9lt_7phGkt6BJC4'


async def main():
    dp.include_routers(commands_router)
    dp.include_routers(start_router)
    dp.include_routers(teachers_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# bot = Bot(DeleteWebhook(True), token=config.API_TOKEN_NOTIC_BOT, parse_mode=ParseMode.HTML)
    
bot = Bot(token=config.API_TOKEN_NOTIC_BOT, parse_mode=ParseMode.HTML)
# bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)


dp = Dispatcher(storage = MemoryStorage())

logging.basicConfig(level=logging.INFO)

# dp.middleware.setup(LoggingMiddleware())

class States(StatesGroup):
    FULLNAME = State()
    

async def start_handler(msg: types.Message, state: FSMContext):
    user_id = str(msg.from_user.id)
    try:

        client = list(db.clients_base.find({'tg_ids': { "$in" : [user_id] }}))
        teacher = db.teachers_base.find_one({'id_tg': { "$in" : [user_id] }})

        if teacher == None:
            if client == []:
                await bot.send_message(user_id, 'Отлично! Как к Вам обращаться? (Фамилия Имя)')
                
                await state.set_state(States.FULLNAME)
            else:
                await bot.send_message(user_id, 'Вы зарегистрированы', reply_markup=db.base_keyboard)

                for administrator_id in config.administrator_ids:
                    await bot.send_message(administrator_id, f'Пользователь {client[0]["fullname"]} нажал старт')
        else:
            await bot.send_message(user_id, 'Добро пожаловать в бота взаимодействия с учениками.\nЗдесь вы можете отправить домашнее задание и запись урока ученику после урока. Запись урока отправится последнему ученику, с кем начался урок, то есть вы должны отправить запись до начала следующего урока, иначе уже не сможете. А домашне заданее сможете прислать потом, но не позже трех дней, после начала урока. По вопросам или уточнениям обращайтесь к администратору', reply_markup=RKM(keyboard=[[KB(text="Отправить домашнее задание")]], resize_keyboard=True))

    except:
        logger('error', message = traceback.format_exc())


dp.message.register(start_handler, Command('start'))

    
if __name__ == '__main__':
    asyncio.run(main())





