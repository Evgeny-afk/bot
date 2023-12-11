import urllib.request
import telebot
import ssl

context = ssl._create_unverified_context()

bot = telebot.TeleBot('5800611516:AAG_gbX0BS5VXMsChPWJTix2WjVnI0leTjI', parse_mode='HTML')
list_stands: dict = {
    1:'Гостелемед',
    2:'ФМБА',
    3:'Свердловская область',
    4:'ЯНАО',
    5:'Курган',
    6:'Марий Эл',
    7:'Нижний Новгород',
    8:'Дагестан',
    9:'Бурятия',
    10:'Астрахань',
    11:'Пенза',
    12:'Московская область'
}
vertion_file_name: str = 'version.txt'

list_urls: dict = {
    1:'https://gostelemed.ru',
    2:'https://tmk.fmba.gov.ru',
    3:'https://doctor.mis66.ru',
    4:'https://tmk.yamalmed.ru',
    5:'https://telemed.poliklinika45.ru',
    6:'https://tmk.minzdrav12.ru',
    7:'https://telemed.mznn.ru',
    8:'https://tmk.k-vrachu.ru',
    9:'https://tmk.burmed.ru',
    10:'https://telemed30.doctor30.ru',
    11:'https://doctor.promed58.ru',
    12:'https://tmk.telemed.mosreg.ru'
}

help_msg = "/list - список стендов\n/all - версии всех стендов\n{ номер стенда } - версия и дата обновления"

def get_all_stand_version():
    about_all_stand_msg = ''
    # msg = ''
    for item, name in list_stands.items():
        msg = get_stand_version(item)
        try:
            msg = msg[0]
        except IndexError:
            msg = 'менее 1.71'
        item = str(item).strip()
        name = name.strip()
        msg = msg.strip()
        about_all_stand_msg += f'{item:<3}<b>{name:<22}</b>{msg:<6}\n'
    about_all_stand_msg = f'<code>{about_all_stand_msg}</code>'
    return about_all_stand_msg
def get_stand_version(stand_number):
    scr_url = '{url}/{location}'.format(url=list_urls[stand_number], location=vertion_file_name)
    try:
        with urllib.request.urlopen(scr_url,context=context) as response:
           stand_msg = str(response.read(), 'utf-8')
           stand_msg = stand_msg.split(' ')
    except:
        stand_msg = ' '
        return stand_msg
    return stand_msg

def fetch_stand_version(stand_number) -> str:
    stand = get_stand_version(stand_number)
    if not isinstance(stand, str):
        try:
            stand[3]
        except IndexError:
            stand.append('')
    try:
        stand_msg = '{stand}\nВерсия приложения: {vertion}\nДата обновления: {date} {time} {zone}\n'.format(stand=list_stands[stand_number], vertion=stand[0], date=stand[1], time=stand[2], zone=stand[3])
        # stand_msg = '<a href="{list_urls[stand_number]}">{stand}<a>\nВерсия приложения: {vertion}\nДата обновления: {date} {time} {zone}\n'.format(stand=list_stands[stand_number], vertion=stand[0], date=stand[1], time=stand[2], zone=stand[3])
    except IndexError:
        stand_msg = '{stand}\nВерсия приложения {vertion}\n'.format(stand=list_stands[stand_number],vertion='менее 1.71')
    stand_msg = f'<code>{stand_msg}</code>'
    return stand_msg

def stand_list_msg():
    list_msg = ''
    for i, name in list_stands.items():
        list_msg = list_msg + f'{i:<5}<a href="{list_urls[i]}">{name:<20}</a><a href="{list_urls[i]}"></a>\n'
    list_msg = f'<code>{list_msg}</code>'
    return list_msg

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    try:
        input_msg = message.text.split(' ')[1]
    except:
        input_msg = message.text
    if input_msg == "/list":
        msg = stand_list_msg()
        bot.send_message(message.chat.id, msg)
    elif input_msg == "/all":
        about_all_stand_msg = get_all_stand_version()
        bot.send_message(message.chat.id, about_all_stand_msg)
    elif input_msg.isdigit():
        stand_number = int(input_msg)
        try:
            about_stand_msg = fetch_stand_version(stand_number)
            bot.send_message(message.chat.id, about_stand_msg)
        except KeyError:
            len_dict_msg = 'Номер стенда не можeт превышать {len_dict}\n/list - список стендов \n/all - версии всех стендов'.format(len_dict=len(list_stands))
            bot.send_message(message.chat.id, len_dict_msg)
    elif input_msg == "/help":
        bot.send_message(message.from_user.id, help_msg)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")

bot.polling(none_stop=True, interval=0)
