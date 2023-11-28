import urllib.request
import telebot


bot = telebot.TeleBot('5800611516:AAG_gbX0BS5VXMsChPWJTix2WjVnI0leTjI')
vertion_file_name = 'version.txt'
list_stands = {
    1:'Гостелемед',
    3:'Свердловская область',
    4:'ЯНАО',
    5:'Курган',
    6:'Марий Эл',
}
list_urls = {
    1:'https://gostelemed.ru',
    3:'https://doctor.mis66.ru',
    4:'https://tmk.yamalmed.ru',
    5:'https://admin.poliklinika45.ru',
    6:'https://tmk.minzdrav12.ru',
}

help_msg = '/list - список стендов \n { номер стенда } - версия и дата обновления'
def get_stand_version(stand_number) -> dict:
    scr_url = '{url}/{location}'.format(url=list_urls[stand_number],location=vertion_file_name)
    with urllib.request.urlopen(scr_url) as response:
       stand = str(response.read(), 'utf-8')
       stand = stand.split(' ')
    try:
        stand_msg = 'Версия приложения {vertion}\nДата обновления {date} {time}\nTimeZone {zone}'.format(vertion=stand[0], date=stand[1], time=stand[2], zone=stand[3])
    except IndexError:
        stand_msg = 'Версия приложения {vertion}\nДата обновления {date} {time}\n'.format(vertion=stand[0], date=stand[1], time=stand[2])
    return stand_msg

def stand_list_msg():
    list_msg = ''
    for i, name in list_stands.items():
        list_msg = list_msg + '{item} \t {stand}'.format(item=i, stand=name) + '\n'
    return list_msg

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    print(message.text)
    print(type(message.text))
    try:
        input_msg = message.text.split(' ')[2]
        print('try')
        print(input_msg)
    except:
        input_msg = message.text
        print(input_msg)
    if input_msg== "/list":
        msg = stand_list_msg()
        bot.send_message(message.chat.id, msg)
    elif input_msg.isdigit():
        stand_number = int(input_msg)
        about_stand_msg = get_stand_version(stand_number)
        bot.send_message(message.chat.id, about_stand_msg)
    elif input_msg== "/help":
        bot.send_message(message.from_user.id, help_msg)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")

bot.polling(none_stop=True, interval=0)
