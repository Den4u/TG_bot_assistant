import time
import os
import logging
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv


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
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение успешно доставлено.')
    except Exception:
        logger.error('Сообщение не было доставлено.')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    payload = {'from_date': int(time.time())}
    try:
        homework_status = requests.get(ENDPOINT, HEADERS, payload)
    except Exception:
        logger.error('Эндпоинт {ENDPOINT} недоступен.')
        raise Exception('Эндпоинт {ENDPOINT} недоступен.')
    if homework_status.status_code != HTTPStatus.OK:
        logger.error('Код ответа API: {homework_statuses.status_code}')
        raise Exception('Код ответа API: {homework_statuses.status_code}')
    try:
        return homework_status.json()
    except Exception:
        logger.error('Ошибка преобразования к формату json.')
        raise Exception('Ошибка преобразования к формату json.')


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if type(response) != dict:
        logger.error('Тип данных не соотвествует словарю.')
        raise TypeError('Тип данных не соотвествует словарю.')
    if 'homeworks' not in response:
        logger.error('Ошибка ключа')
        raise KeyError('Ошибка ключа')
    homeworks_response = response['homeworks']
    if type(homeworks_response) != list:
        logger.error('Тип данных не соотвествует списку.')
        raise TypeError('Тип данных не соотвествует списку.')
    return homeworks_response


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        logger.error('Ошибка ключа.')
        raise KeyError('Ошибка ключа.')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('Неизвестный статус.')
        raise ValueError('Неизвестный статус.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_status = ''
    if not check_tokens():
        logger.critical('Отсутсвуют переменные окружения')
        raise KeyError('Отсутсвуют переменные окружения')
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not len(homework):
                logger.info('Статус не обновлен')
            else:
                homework_status = parse_status(homework[0])
                if current_status == homework_status:
                    logger.info(homework_status)
                else:
                    current_status = homework_status
                    send_message(bot, homework_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
