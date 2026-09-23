import csv
from pathlib import Path
from typing import Any

from .errors import StorageError, ValidationError
from .service import add_copy

CSV_COLUMNS = ["copy_id", "title", "author", "isbn"]


def import_copies(
    data: dict[str, Any], csv_path: Path
) -> tuple[dict[str, Any], list[tuple[int, str]]]:
    updated = data
    imported: list[tuple[int, str]] = []
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != CSV_COLUMNS:
                expected = ",".join(CSV_COLUMNS)
                raise ValidationError(f"CSV 表头必须严格为 {expected}")

            for row in reader:
                line_number = reader.line_num
                if None in row or any(
                    not isinstance(row.get(column), str) for column in CSV_COLUMNS
                ):
                    raise ValidationError(f"CSV 第 {line_number} 行：列数或字段无效")
                isbn = row["isbn"].strip() or None
                try:
                    updated = add_copy(
                        updated,
                        row["copy_id"],
                        row["title"],
                        row["author"],
                        isbn,
                    )
                except ValidationError as exc:
                    raise ValidationError(f"CSV 第 {line_number} 行：{exc}") from exc
                imported.append((line_number, row["copy_id"].strip()))
    except UnicodeDecodeError as exc:
        raise ValidationError(f"CSV 文件 {csv_path} 不是有效的 UTF-8 文本") from exc
    except csv.Error as exc:
        raise ValidationError(f"CSV 文件 {csv_path} 格式错误：{exc}") from exc
    except OSError as exc:
        raise StorageError(f"无法读取 CSV 文件 {csv_path}: {exc}") from exc
    return updated, imported
