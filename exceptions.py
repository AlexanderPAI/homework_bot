class Code200Error(Exception):
    """Исключение для status_code!=200."""

    def __init__(self, status_code):
        """Объявление исключения."""
        self.status_code = status_code
        self.message = (f'Ошибка доступа к API: status_code!=200.'
                        f'Status_code={status_code}')

    def __str__(self):
        """Исключение для status_code!=200."""
        return self.message
