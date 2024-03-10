class EnvironmentVariableError(Exception):
    """Отсутствие обязательной переменной окружения."""

    ...


class InternalServerError(Exception):
    """Ошибка на сервере."""

    ...


class TokenError(Exception):
    """Неверный токен."""

    ...


class FormDateError(Exception):
    """Неверный формат from_date."""

    ...


class NoContentError(Exception):
    """Отсутствие контента."""

    ...


class IncorrectAPIDataError(Exception):
    """Отсутствие необходимых ключей в ответе API."""

    ...


class Error404(Exception):
    """Неверный URL."""

    ...
