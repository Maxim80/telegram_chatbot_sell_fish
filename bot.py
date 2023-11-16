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
import api


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


def start(update: Update, context: CallbackContext) -> str:
    products = api.get_products()

    keyboard = [
        [InlineKeyboardButton(text=product['attributes']['title'], callback_data=product['id'])]
        for product in products
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handler_menu(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    product_id = query.data
    chat_id = query.message.chat_id
   
    title, description, price, picture = api.get_product_info(product_id)
    caption = f'{title} ({price} руб. за кг)\n\n{description}'
    
    keyboard = [
        [InlineKeyboardButton(text='Назад', callback_data='back')],
        [InlineKeyboardButton(text='Добавить в корзину', callback_data=product_id)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.bot.send_photo(chat_id=chat_id, photo=picture, caption=caption, reply_markup=reply_markup)

    previous_message_id = query.message.message_id
    query.bot.delete_message(chat_id=chat_id, message_id=previous_message_id)
    return 'HANDLE_DESCRIPTION'


def handler_description(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if query.data != 'back':
        tg_id = query.from_user.id
        cart = api.get_cart(tg_id)
        if not cart['data']:
            cart = api.create_cart(tg_id)
        
        product_id = query.data
        cart_id = cart['data']['id']
        cart_product = api.create_cart_product(product_id, cart_id)
    query.bot.delete_message(chat_id=chat_id, message_id=message_id)
    return start(query, context)
    

def handler_users_reply(update: Update, context: CallbackContext) -> None:
    state_functions: dict = {
        'START': start,
        'HANDLE_MENU': handler_menu,
        'HANDLE_DESCRIPTION': handler_description,
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
    dispatcher.add_handler(CallbackQueryHandler(handler_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handler_users_reply))
    dispatcher.add_handler(CommandHandler('start', handler_users_reply))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
