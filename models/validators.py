import re

from tortoise.exceptions import ValidationError
from tortoise.validators import Validator


class EmailValidator(Validator):
    """
    Валидатор почты
    """
    def __call__(self, value: str):
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not re.match(email_pattern, value):
            raise ValidationError("Невалидный email")
