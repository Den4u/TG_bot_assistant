class APINotAvailableError(Exception):
    """Ошибка соединения с API."""

    pass


class JSONDecodeError(Exception):
    """Ошибка преобразования к формату JSON."""

    pass


class InvalidHTTPResponseError(Exception):
    """Неверный код ответа API."""

    pass


class SendMessageError(Exception):
    """Ошибка отправки сообщения."""

    pass
