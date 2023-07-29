# poker_collector
# бот для покерных расчетов. 
# на вход принимает результаты из лог леджер с указаниями + - кто сколько выиграл/проиграл
# на выход выдает кто кому должен сколько перевести.
# валидация:
# 1) на месте имен имена, на месте цифр цифры.
# 2) перед цифрами знак + или -. Если знака нет, то цифра должна быть 0
# 3) сумма равна нулю.
# еще одну версию

import telebot
import re
import operator
import requests
import json
import os, sys, inspect
from dotenv import load_dotenv


def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)
# основной метод расчета

def url_request_decorator(func, message):
    def wrapper(message):
        if message[:32].lower() == "https://www.pokernow.club/games/":
            preparedMessage = "Расчет"
            ledger = get_ledger(message)
            ledger1 = json.loads(ledger)
            ledgerResults = ledger1["playersInfos"].items()
            print (len(ledgerResults))
            # переписать когда будем добавлять мэппинг
            for a in ledgerResults:
                preparedMessage += "\n"
                preparedMessage += str(a[1]["names"][0]) + " "
                preparedMessage += str(a[1]["net"])

            # преобразовать ledger в массив "имя" "ник" "результат". Ник пока оставляем не заполненным.
            # print (preparedMessage)

            return func(str(preparedMessage))
        return func(message)
    return wrapper (message)

def get_ledger(urlString):

    response = requests.get(urlString+'/players_sessions')
    # print (response.text)
    return response.text.lstrip()
    

def main_mod(message):
    # calcResults = "я получил твое сообщение \"" + message.text + "\" , но пока не знаю что с ним делать."
    # return (calcResults)

    textArr  = message.split("\n")
    textArr = textArr[1:]
    validationResult = textValidation(textArr)
    if validationResult[0] == True:
        return calculation(textArr)
    else:
        return validationResult[1]

def calculation (textArr):
    positiveList = []
    negativeList = []
    finalText = ""

    for textRow in textArr:
    # вычисляем сумму
    # если ноль, то пропускаем полностью.
        person = []

        if textRow.split(" ")[-1] == "0":
            continue
        sign = textRow.split(" ")[-1][0]
        if sign == "+" or sign == "-":
            number = (textRow.split(" ")[-1])[1:]
        elif sign in ('123456789'):
            sign = "+"
            number = (textRow.split(" ")[-1])


        if sign == "+":
            amount = int(number)
        elif sign == "-":
            amount = 0 - int(number)
        else:
            continue
    # вычисляем имя
        name = ""
        for x in textRow.split(" ")[:-1]:
            name = name + x + " "
        name = name[:-1]
    # собираем список
        person.append(name)
        person.append(amount)
        if person[1] > 0:
            positiveList.append(person)
        else:
            negativeList.append(person)    

    # сортируем списоки
    positiveList = sorted(positiveList, key=operator.itemgetter(1), reverse = True)
    negativeList = sorted(negativeList, key=operator.itemgetter(1), reverse = True)
 
    # проходим по плюсовикам
    for r in positiveList:
        while r[1] > 0:
            if r[1] + negativeList[0][1] > 0:
                transactionString = (negativeList[0])[0] + " -> " + r[0] + " " + str(0 -negativeList[0][1])
                r[1] += (negativeList[0])[1]
                negativeList.pop(0)
            elif r[1] + (negativeList[0])[1] == 0:
                transactionString = (negativeList[0])[0] + " -> " + r[0] + " " + str(0 - (negativeList[0])[1])
                r[1] = 0
                negativeList.pop(0)
            else:
                transactionString = (negativeList[0])[0] + " -> " + r[0] + " " + str(r[1])
                (negativeList[0])[1] += r[1]
                r[1] = 0
            finalText = finalText + transactionString + "\n"
    return finalText

def textValidation(textArr):
    a = True
    t = ""
    controllSum = 0
    # Проверяем что строка заканчивается числом и что либо перед числом стоит знак либо оно нуль
    for textRow in textArr:
        if textRow.split(" ")[-1] == "0":
            continue
        sign = textRow.split(" ")[-1][0]
        if sign == "+" or sign == "-":
            number = (textRow.split(" ")[-1])[1:]
        elif sign in ('123456789'):
            sign = "+"
            number = (textRow.split(" ")[-1])
        if bool(re.fullmatch(r'\d+$',(number))):
            if sign == "+" or sign in ('123456789'):
                controllSum += int(number)
            elif sign == "-":
                controllSum -= int(number)
            else:
                a = False
                t = "сумму вижу, а выиграл или проиграл - не вижу. \n" + textRow
                return [a,t]
        else:
            a = False
            t = "сумму не вижу. Или вижу, но понять не могу. \n" + textRow
            return [a,t]
    if controllSum != 0:
        a = False
        t = "считать не умеешь блеать? в сумме ноль должен быть!"
        return [a,t]
    return [a,t]

# создать бота
os.chdir(get_script_dir())

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)
token = os.environ.get('TOKEN')

bot = telebot.TeleBot(str(token))
# кнопка /start

@bot.message_handler(commands=['start'])
def start(m, res=False):
    bot.send_message(m.chat.id, 'здарова заебал. Отправь сюда результаты как покатали')

# получить сообщение от пользователя
@bot.message_handler(content_types=['text'])
def message_handler(message):
    if message.text[:6].lower() == "расчет":
        bot_response = main_mod(message.text)
        bot.send_message(message.chat.id, bot_response)
    elif message.text[:32].lower() == "https://www.pokernow.club/games/":
        bot.send_message(message.chat.id, url_request_decorator(main_mod, message.text))


# запускаем бота
bot.infinity_polling()
