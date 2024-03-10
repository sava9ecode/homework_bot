import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from requests import RequestException

from exceptions import (
    EnvironmentVariableError,
    Error404,
    FormDateError,
    IncorrectAPIDataError,
    InternalServerError,
    NoContentError,
    TokenError,
)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s %(funcName)s %(lineno)d'
)

handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

ERROR_MESSAGE = {
    'InternalServerError': 'Ошибка на сервере',
    'TokenError': 'Неверный токен',
    'FormDateError': 'Неверный формат from_date',
    'NoContentError': 'Запрос выполнен, ничего не следует',
    'Error404': 'Неверный URL',
    'TypeError': 'Неверный ответ API',
    'IncorrectAPIDataError': 'Отсутствие необходимых ключей в ответе API',
    'EnvironmentVariableError': (
        'Отсутствует обязательная переменная окружения. '
        'Приложение было принудительно остановлено.'
    )
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено')
    except Exception as error:
        logger.error(
            f'Ошибка при отправке сообщения в Telegram: {error}'
        )


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )

        match response.status_code:
            case HTTPStatus.INTERNAL_SERVER_ERROR:
                raise InternalServerError(
                    ERROR_MESSAGE.get('InternalServerError')
                )
            case HTTPStatus.UNAUTHORIZED:
                raise TokenError(ERROR_MESSAGE.get('TokenError'))
            case HTTPStatus.BAD_REQUEST:
                raise FormDateError(ERROR_MESSAGE.get('FormDateError'))
            case HTTPStatus.NO_CONTENT:
                raise NoContentError(ERROR_MESSAGE.get('NoContentError'))
            case HTTPStatus.NOT_FOUND:
                raise Error404(ERROR_MESSAGE.get('Error404'))

        return response.json()
    except RequestException as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not (
        'homeworks' in response
        and isinstance(response.get('homeworks'), list)
        and isinstance(response, dict)
    ):
        raise TypeError(ERROR_MESSAGE.get('TypeError'))


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус."""
    homework_name = homework.get('homework_name')
    homework_verdict = HOMEWORK_VERDICTS.get(homework.get('status'))

    if not (homework_name and homework_verdict):
        raise IncorrectAPIDataError(
            ERROR_MESSAGE.get('IncorrectAPIDataError')
        )

    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f' {homework_verdict}'
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(ERROR_MESSAGE.get('EnvironmentVariableError'))
        raise EnvironmentVariableError

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    ERROR_MESSAGE_SEND_STATUS = {
        ERROR_MESSAGE.get('InternalServerError'): False,
        ERROR_MESSAGE.get('TokenError'): False,
        ERROR_MESSAGE.get('FormDateError'): False,
        ERROR_MESSAGE.get('NoContentError'): False,
        ERROR_MESSAGE.get('Error404'): False,
        ERROR_MESSAGE.get('TypeError'): False,
        ERROR_MESSAGE.get('IncorrectAPIDataError'): False,
    }

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)

            homeworks = response.get('homeworks')
            for homework in homeworks:
                message = parse_status(homework)

            if not homeworks:
                message = 'Обновлений нет'
                logger.debug(message)

            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'

            if not ERROR_MESSAGE_SEND_STATUS.get(str(error)):
                ERROR_MESSAGE_SEND_STATUS[str(error)] = True
                send_message(bot, message)

            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
