import telebot
import config
import secretdata
import similarity
import inspect
import asyncio
import requests

bot = telebot.TeleBot(secretdata.token)

savedata = {}

keyboard_main = telebot.types.ReplyKeyboardMarkup(True)
keyboard_main.row('Сократить ссылку', 'Список сокращённых')

keyboard_cancel = telebot.types.ReplyKeyboardMarkup(True)
keyboard_cancel.row('Отмена')


@bot.message_handler(commands=['start'])
def start_message(message):
    out_message = inspect.cleandoc('''
            Привет, я бот сокращающий url.
            Можешь воспользоваться как командами, так и кнопками ниже.
            /minurl для сокращения url
            /histurl для показа последних сокращённых url
            ''')
    bot.send_message(message.chat.id, out_message, reply_markup=keyboard_main)


@bot.message_handler(commands=['help'])
def help_message(message):
    out_message = inspect.cleandoc('''
            /minurl для сокращения url
            /histurl для показа последних сокращённых url
            ''')
    bot.send_message(message.chat.id, out_message)


@bot.message_handler(commands=['minurl'])
def min_url_message(message):
    # Создание триггера ожидания для конкретного чата
    savedata[str(message.chat.id) + 'inputurl'] = 'wait'
    bot.send_message(message.chat.id, 'Введи ссылку для сокращения',
                     reply_markup=keyboard_cancel)


@bot.message_handler(commands=['histurl'])
def hist_url_message(message):
    key = str(message.chat.id) + 'listurl'
    if key in savedata:
        list_last_url = '\n'.join(savedata[str(message.chat.id) + 'listurl'])
    else:
        list_last_url = 'Список пуст'
    bot.send_message(message.chat.id, list_last_url,
                     disable_web_page_preview = True)
    bot.send_sticker(message.chat.id, config.sticker_bang)


@bot.message_handler(content_types=["text"])
def test_message(message):
    # Если стоит триггер ожидания ввода inputurl, выполняем
    key = str(message.chat.id) + 'inputurl'
    if key in savedata and savedata[key] == 'wait':
        savedata[key] = None
        if message.text.lower() == 'отмена':
            bot.send_message(message.chat.id, 'Окей',
            	             reply_markup=keyboard_main)
        else:
            bot.send_message(message.chat.id, 'Один момент, сейчас обработаю',
                             reply_markup=keyboard_main)
            # выполнение функции запроса сокращённой ссылки и ответа асинхронно
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(min_url_request(message))
    else:
        # Воспользуемся простым коэффициентом Танимото,
        # он плохо подходит для маленьких слов, поэтому
        # для них просто сделаем жёсткое сравнение
        if similarity.tanimoto(message.text.lower(), 'список сокращённых') >= 0.70:
            hist_url_message(message)
        elif similarity.tanimoto(message.text.lower(), 'сократить ссылку') >= 0.70:
            min_url_message(message)
        elif message.text.lower() in ('спасибо', 'спс', 'спасиб')
          or message.text.lower() in ('привет', 'даров', 'хэлло'):
            bot.send_sticker(message.chat.id, config.sticker_thank)
        else:
            bot.send_message(message.chat.id, 'Я не знаю как ответить',
                             reply_markup=keyboard_main)


async def min_url_request(message):
    create_url = 'https://rel.ink/api/links/'
    url_to_reduce = {'url': message.text}
    create_answer = requests.post(create_url, data = url_to_reduce)
    # Обработка ошибки
    if create_answer.json()["url"][0] == 'Enter a valid URL.':
        bot.send_message(message.chat.id,
        	             'Введите, пожалуйста, корректный url')
        return
    shortened_url = 'https://rel.ink/' + create_answer.json()["hashid"]
    key = str(message.chat.id) + 'listurl'
    if key not in savedata:
        savedata[key] = []
    savedata[key].append(shortened_url)
    # Удаляем лишние записи из начала
    if len(savedata[key]) > config.max_len_url_list:
        savedata[key].pop(0)
    out_message = 'Ваша сокращённый url: ' + shortened_url +
                  '\nПолный url: ' + message.text
    bot.send_message(message.chat.id, out_message,
                     disable_web_page_preview = True)


if __name__ == '__main__':
    bot.infinity_polling()
