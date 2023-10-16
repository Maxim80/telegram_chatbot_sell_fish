from telegram.ext import Updater, Filters
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.dispatcher import Dispatcher
from telegram.update import Update
from dotenv import dotenv_values
from redis import Redis
from collections import OrderedDict
from typing import Optional
import requests
import json
import os


_database: Optional[Redis] = None


def get_database_connection() -> Redis:
    global _database
    if _database is None:
        config: OrderedDict = dotenv_values('.env')
        _database = Redis(
            host=config['REDIS_HOST'],
            port=config['REDIS_PORT'],
            password=config['REDIS_PASSW'] 
        )
    return _database


def get_response_from_strapi(url, params=None):
    base_url = 'http://localhost:1337'
    response = requests.get(base_url + url, params=params)
    response.raise_for_status()
    return response.content


def start(update: Update, context: CallbackContext) -> str:
    params = {
        'pagination[page]': 1,
        'pagination[pageSize]': 10,
    }
    products_url = '/api/products/'
    products_info = json.loads(get_response_from_strapi(products_url, params))
    products = products_info['data']
    page = products_info['meta']['pagination']['page']
    page_count = products_info['meta']['pagination']['pageCount']
    while page_count - 1 > 0:
        params['pagination[page]'] += 1
        page_count -= 1
        products.extend(json.loads(get_response_from_strapi(products_url, params))['data'])

    keyboard = [
        [InlineKeyboardButton(product['attributes']['title'], callback_data=product['id'])]
        for product in products
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    product_id = query.data
    product_url = f'/api/products/{product_id}'
    params = {
        'populate[0]': 'picture',
    }
    product = json.loads(get_response_from_strapi(product_url, params))
    product_title = product['data']['attributes']['title']
    product_description = product['data']['attributes']['description']
    product_price = product['data']['attributes']['price']
    picture_url = product['data']['attributes']['picture']['data'][0]['attributes']['formats']['medium']['url']
    picture = get_response_from_strapi(picture_url)
    caption = f'{product_title} ({product_price} руб. за кг)\n\n{product_description}'
    chat_id = query.message.chat_id
    query.bot.send_photo(chat_id, picture, caption=caption)
    return 'START'


def handle_users_reply(update: Update, context: CallbackContext) -> None:
    state_functions: dict = {
        'START': start,
        'HANDLE_MENU': handle_menu,
    }

    db: Redis = get_database_connection()

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    
    user_state = 'START' if user_reply == '/start' else db.get(chat_id).decode('utf-8')

    state_handler = state_functions[user_state]
    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def main() -> None:
    config: OrderedDict = dotenv_values('.env')
    telegram_token: str = config['TELEGRAM_TOKEN']

    updater: Updater = Updater(telegram_token)
    dispatcher: Dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
