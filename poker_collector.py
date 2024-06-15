# poker_collector v 3.1.4
# бот для покерных расчетов. 
# на вход принимает результаты из лог леджер с указаниями + - кто сколько выиграл/проиграл
# на выход выдает кто кому должен сколько перевести.
# валидация:
# 1) на месте имен имена, на месте цифр цифры.
# 2) перед цифрами знак + или -. Если знака нет, то цифра должна быть 0
# 3) сумма равна нулю.
# 3.1.4:
# 1) обращение к незарегистрированным игрокам
 
import telebot
import re
import operator
import requests
import json
import os, sys, inspect
from pymongo import MongoClient
from dotenv import load_dotenv


global unknownSquad
unknownSquad = ""

def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)
# основной метод расчета

def url_request_decorator(func, message, mode):
    def wrapper(message):
        if message[:37].lower() == "итог https://www.pokernow.club/games/":
            preparedMessage = "Расчет"
            i=0
            global unknownSquad
            while message.find("https://www.pokernow.club/games/")>=0:
                i+=1 # считаем циклы чтобы не бегать в базу больше 1 раза
                link_start = message.find("https://www.pokernow.club/games/")
                message = message [link_start:]
                link_end = message.find(" ")
                if link_end == -1:
                    link_end = len(message)
                ledger = get_ledger(message[:link_end])
                ledger1 = json.loads(ledger)
                ledgerResults = ledger1["playersInfos"].items()
                print (len(ledgerResults))
                # переписать когда будем добавлять мэппинг
                if mode == 1 and i==1:
                    client = MongoClient('mongodb+srv://' + mongo_user + ":" + mongo_pass + mongo_client_tail)
                    db = client['Collector_DB_TEST']
                    collection = db ['players']
                    downloadedCollection = collection.find()
                    print (downloadedCollection)
                    userDict = {}
                    for x in downloadedCollection:
                        print(x)
                        userDict[x["pn_userid"]] = x["tg_uname"] + " // " + x["tel"] + " $$ "+ x["banks"]
                for a in ledgerResults:
                    preparedMessage += "\n"
                    if mode == 1:
                        playerId = str(a[0])
                        print (playerId)
                        try:
                            playerId = userDict [str(a[0])]
                            preparedMessage += playerId[:playerId.find("// ")] + " (aka "
                            preparedMessage += str(a[1]["names"][0]) + ") "
                            preparedMessage += playerId[playerId.find(" // "):] + " "
                            preparedMessage += str(a[1]["net"])

                            print("success! Player "+ str(a[0]) + " was recognized as " + playerId)
                        except Exception as e:
                            print("player " + playerId + " not found!")
                            preparedMessage += playerId + " (aka "
                            preparedMessage += str(a[1]["names"][0]) + ") "
                            preparedMessage += str(a[1]["net"])
                            unknownSquad += str(a[1]["names"][0]) + ", "
                    else:
                        preparedMessage += str(a[1]["names"][0]) + " "
                        preparedMessage += str(a[1]["net"])
                message = message[link_end-1:]
            # преобразовать ledger в массив "имя" "ник" "результат". Ник пока оставляем не заполненным.
            # print (preparedMessage)

            return func(str(preparedMessage), mode)
        return func(message, mode)
    return wrapper (message)

def get_ledger(urlString):

    response = requests.get(urlString+'/players_sessions')
    # print (response.text)
    return response.text.lstrip()
    

def main_mod(message, operating_mode):
    # calcResults = "я получил твое сообщение \"" + message.text + "\" , но пока не знаю что с ним делать."
    # return (calcResults)

    textArr  = message.split("\n")
    textArr = textArr[1:]
    validationResult = textValidation(textArr)
    if validationResult[0] == True:
        metarow = "#расплата: \n"
        return metarow + calculation(textArr)
    else:
        return validationResult[1]
    
def calculation (textArr):
    ResultDict = {}

    positiveList = []
    negativeList = []
    finalText = ""

    for textRow in textArr:
    # вычисляем сумму
    # если ноль, то пропускаем полностью.

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
    # добавляем в словарь. Если имя уже встречалось, то прибавляем результат
        if name in ResultDict:
            ResultDict[name] += amount
        else:
            ResultDict[name] = amount

    # собираем список из листа
    for t in ResultDict.keys():
        person = []
        person.append(t)
        person.append(ResultDict[t])
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
            negativeNameEnd = negativeList[0][0].find(" // ")
            if negativeNameEnd >=0:
                negativeName = negativeList[0][0][:negativeNameEnd]
            else:
                negativeName = negativeList[0][0]

            positiveNameEnd = r[0].find(" // ")
            if positiveNameEnd >= 0:
                positiveName = r[0][:positiveNameEnd]
                positiveTel = " тел.: " + r[0][positiveNameEnd+4:r[0].find(" $$ ")]
                positiveBank = " в " + r[0][r[0].find(" $$ ")+4 :]
            else:
                positiveName = r[0]
                positiveTel = ""
                positiveBank = ""
            if r[1] + negativeList[0][1] > 0:                
                transactionString = negativeName + " -> " + positiveName + "\n" + str(0 -negativeList[0][1]) + " ₽" + positiveTel + positiveBank
                r[1] += (negativeList[0])[1]
                negativeList.pop(0)
            elif r[1] + (negativeList[0])[1] == 0:
                transactionString = negativeName + " -> " + positiveName + "\n" + str(0 - (negativeList[0])[1]) + " ₽" + positiveTel + positiveBank
                r[1] = 0
                negativeList.pop(0)
            else:
                transactionString = negativeName + " -> " + positiveName + "\n" + str(r[1]) + " ₽" + positiveTel + positiveBank
                (negativeList[0])[1] += r[1]
                r[1] = 0
            finalText = finalText + transactionString + "\n\n"
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
VIP_chat_id = os.environ.get('VIP_CHAT_CODE')
VIP_chat_welcome_text = os.environ.get('VIP_CHAT_WELCOME_TEXT')
VIP_chat_gdoc_reg = os.environ.get('VIP_CHAT_GDOC_REGISTRATION')
mongo_client_tail = os.environ.get('MONGO_CLIENT_TAIL')
mongo_user = os.environ.get('MONGO_USER')
mongo_pass = os.environ.get('MONGO_PASS')

bot = telebot.TeleBot(str(token))
# кнопка /start

@bot.message_handler(commands=['start'])
def start(m, res=False):
    bot.send_message(m.chat.id, 'здарова заебал. Отправь сюда результаты как покатали.\nОтправь сообщение, которое начинается со слова "итог " и ссылки на игру в pokernow. \n \n ПРИМЕР: \nитог https://www.pokernow.club/games/pglFzhAquDgdi8luFX_WHAsXH')

# получить сообщение от пользователя
@bot.message_handler(content_types=['text'])
def message_handler(message):
    func_mode = 0 # общий режим работы
    if message.text[:6].lower() == "расчет":        
        bot_response = main_mod(message.text, 0)
        bot.send_message(message.chat.id, bot_response)
    elif message.text[:37].lower() == "итог https://www.pokernow.club/games/":
        if str(message.chat.id) == VIP_chat_id:
            func_mode = 1 # режим работы для VIP чата
            main_results = url_request_decorator(main_mod, message.text, func_mode)
            end_message = ""
            if unknownSquad != "":
                end_message = "\n" + "👹 " + unknownSquad + "\n КТО ВЫ? Я ВАС НЕ ЗНАЮ! ИДИТЕ НА pokernow.club, зарегистрируйтесь там и заполните анкету " + VIP_chat_gdoc_reg + "\n Играйте, пожалуйста, зарегистрированными! Спасибо."
            bot_response = VIP_chat_welcome_text + "\n" + main_results + end_message            
        else:
            bot_response = url_request_decorator(main_mod, message.text, func_mode)
        bot.send_message(message.chat.id, bot_response)

# запускаем бота
bot.infinity_polling()
