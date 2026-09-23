from .errors import ValidationError


def compact_isbn(value: str) -> str:
    return "".join(character for character in value if not character.isspace() and character != "-").upper()


def normalize_isbn(value: str) -> str:
    compact = compact_isbn(value)
    if len(compact) == 10:
        if not compact[:9].isdigit() or not (compact[9].isdigit() or compact[9] == "X"):
            raise ValidationError("ISBN-10 格式无效")
        digits = [int(character) for character in compact[:9]]
        check_digit = 10 if compact[9] == "X" else int(compact[9])
        checksum = sum((10 - index) * digit for index, digit in enumerate(digits))
        checksum += check_digit
        if checksum % 11 != 0:
            raise ValidationError("ISBN-10 校验位无效")
        return compact

    if len(compact) == 13:
        if not compact.isdigit() or not compact.startswith(("978", "979")):
            raise ValidationError("ISBN-13 格式无效")
        checksum = sum(
            int(character) * (1 if index % 2 == 0 else 3)
            for index, character in enumerate(compact[:12])
        )
        expected = (10 - checksum % 10) % 10
        if int(compact[12]) != expected:
            raise ValidationError("ISBN-13 校验位无效")
        return compact

    raise ValidationError("ISBN 必须是 10 位或 13 位")

