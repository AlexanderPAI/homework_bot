import logging
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
from os import getenv


from exceptions import Code200Error

load_dotenv()


PRACTICUM_TOKEN = getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


# Настройка логирования
logging.basicConfig(
    level=logging.NOTSET,
    format='%(asctime)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности обязательных переменных окружения."""
    env_vars = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]

    for env_var in env_vars:
        if env_var is None:
            logging.critical('Не доступна обязательная перемменная окружения')
            sys.exit()


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API Практикум.Домашка."""
    try:
        payload = {'from_date': timestamp}
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.RequestException as error:
        return f'Ошибка доступа к API {error}'

    if response.status_code != HTTPStatus.OK:
        raise Code200Error(response.status_code)

    response = response.json()
    return response


def check_response(response):
    """Проверка ответа API на соответствие документации API."""
    if not isinstance(response, dict):
        raise TypeError(f'Получен {type(response)} вместо ожидаемого словаря')
    if 'homeworks' not in response.keys():
        raise KeyError('В ответе API нет ключа "homeworks"')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(f'homeworks не является списком, возвращается'
                        f'в виде {type(response.get("homeworks"))}')
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework):
    """Получение статуса домашней работы из ответа API."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if status not in HOMEWORK_VERDICTS.keys():
        raise KeyError('API возвращает недокументаированный'
                       'либо пустой статус домашней работы')
    if homework_name is None:
        raise KeyError('В ответе API нет ключа "homework_name"')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    last_answer = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message == last_answer:
                    logging.debug('Проверка обновлений статуса: изменений нет')
                else:
                    last_answer = message
                    send_message(bot, message)
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
