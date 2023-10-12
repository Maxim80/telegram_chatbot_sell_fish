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


def get_response_from_strapi(page=1, page_size=10, product_id=None):
    base_url = 'http://localhost:1337/api/products/'
    if product_id:
        response = requests.get(base_url + str(product_id))
    else:
        params = {
            'pagination[page]': page,
            'pagination[pageSize]': page_size,
        }
        response = requests.get(base_url, params=params)
    
    return json.loads(response.text)


def start(update: Update, context: CallbackContext) -> str:
    products_info = get_response_from_strapi()
    products = products_info['data']
    page = products_info['meta']['pagination']['page']
    page_count = page = products_info['meta']['pagination']['pageCount']
    while page_count - 1 > 0:
        page += 1
        page_count -= 1
        products.extend(get_response_from_strapi(page=page)['data'])

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
    user_selection = query.data
    query.edit_message_text(text=f"Selected option: {query.data}")
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
