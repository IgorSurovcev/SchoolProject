from pymongo import MongoClient
from pymongo.server_api import ServerApi

from aiogram import types
from aiogram.types import KeyboardButton as KB, ReplyKeyboardMarkup as RKM

import config



class DB_Mongo:
    def __init__(self):
        self.client = MongoClient(f"mongodb://igor:{config.password_db}@45.9.42.119:27017/?authMechanism=DEFAULT", server_api=ServerApi('1'))
        self.db = self.client['school_db']

        self.clients_base = self.db['clients']
        self.teachers_base = self.db['teachers']
        self.records_base = self.db['records']
        self.transactions_base = self.db['transactions']
        self.records_templates_base = self.db['records_templates']
        self.events_base = self.db['events']

        self.logs = self.db['logs']

        self.subjects = {
                            'Математика': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]}, 
                            'Русский язык': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]}, 
                            'Химия': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]},
                            'Биология': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]},
                            'Литература': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]}, 
                            'Информатика': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]}, 
                            'Физика': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]},
                            'Обществознание': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]},
                            'Китайский язык': {'price-cost':[{'price':[600, 6000], 'cost':300}, {'price':[990, 9900], 'cost':600}, {'price':[1500, 15000], 'cost':1000}], 'id_main_teachers':[23454]}
                        }
        self.texts = {
                        'Клиент с абонементом': 
                            'Добрый день! 😊\nСегодня в {hour}:{minute} запланирован урок по {subject}!',

                        'Клиент без абонемента': 
                            'Добрый день! 😊\nСегодня в {hour}:{minute} запланирован урок по {subject}!', # button to pay record

                        'Клиент c заканчивающимся абонементом': 
                            'Добрый день! 😊\nСегодня в {hour}:{minute} запланирован урок по {subject}!\n--\n\На балансе абонемента остался 1 урок. Не забудьте продлить его перед следующим занятием.'
                    }
        
        self.bank_codes = {
            'Сбербанк': 'bank100000000111', 
            'Тинькофф': 'bank100000000004',
            'Альфа-Банк': 'bank100000000008',
            'Райффайзенбанк': 'bank100000000007',
            'Открытие' : 'bank100000000015',
            'Газпромбанк' : 'bank100000000001',
            'Россельхозбанк' : 'bank100000000020',
            'Почта банк': 'bank100000000016'
        }

        self.base_keyboard = RKM(keyboard=[[KB(text="Следующий урок")],[KB(text="Неоплаченные уроки")]], resize_keyboard=True)

        

db = DB_Mongo()