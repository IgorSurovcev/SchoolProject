from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup as RKM, InlineKeyboardMarkup as IKM, KeyboardButton as KB, InlineKeyboardButton as IKB

from aiohttp import web
import config

bot = Bot(token=config.API_TOKEN_NOTIC_BOT)
router = web.RouteTableDef()

@router.get('/send_message')
async def index(request):
    user_id = int(request.rel_url.query['user_id'])
    text = request.rel_url.query['text']
    meeting_link = request.rel_url.query.get('meeting_link', '') 
    payment_link = request.rel_url.query.get('payment_link', '')  
    # print('payment_link')
    keyboard = []
    
    if meeting_link != '': 
        keyboard.append([IKB(text='Перейти на урок', url=meeting_link)])
    if payment_link != '': 
        keyboard.append([IKB(text='Оплатить', url=payment_link)])

    await bot.send_message(user_id,text, reply_markup=IKM(inline_keyboard=keyboard, resize_keyboard=True))
    return web.Response(text="Success")


if __name__ == "__main__":
    app = web.Application()
    # configure app
    app.add_routes(router)
    web.run_app(app, port=5055)








