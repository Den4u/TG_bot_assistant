import time
import os
import logging
import sys
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

import exceptions as exc


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    filename='program.log',
    filemode='a',
    format='%(asctime)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправка сообщений в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение "{message}" успешно доставлено.')
    except telegram.TelegramError as error:
        message = (f'Сообщение "{message}" не было доставлено: {error}.')
        logger.error(message)
        raise exc.SendMessageError(message)


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    payload = {'from_date': int(time.time())}
    try:
        homework_status = requests.get(ENDPOINT, HEADERS, payload)
    except Exception as error:
        message = (f'Эндпоинт "{ENDPOINT}" недоступен: {error}.')
        logger.error(message)
        raise exc.APINotAvailableError(message)
    if homework_status.status_code != HTTPStatus.OK:
        message = (f'Ошибка: "{homework_status.status_code}".')
        logger.error(message)
        raise exc.InvalidHTTPResponseError(message)
    try:
        return homework_status.json()
    except Exception as error:
        message = (f'Ошибка преобразования к формату JSON: {error}.')
        logger.error(message)
        raise exc.JSONDecodeError(message)


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if type(response) != dict:
        message = 'Тип данных не соотвествует словарю.'
        logger.error(message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Ошибка ключа.'
        logger.error(message)
        raise KeyError(message)
    homeworks_response = response['homeworks']
    if type(homeworks_response) != list:
        message = 'Тип данных не соотвествует списку.'
        logger.error(message)
        raise TypeError(message)
    return homeworks_response


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        message = 'Ошибка ключа.'
        logger.error(message)
        raise KeyError(message)
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неизвестный статус.'
        logger.error(message)
        raise ValueError(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутсвуют переменные окружения!'
        logger.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not len(homework):
                logger.info('Статус не обновлен.')
            else:
                homework_status = parse_status(homework[0])
                if current_status == homework_status:
                    logger.info(homework_status)
                else:
                    current_status = homework_status
                    send_message(bot, homework_status)
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
