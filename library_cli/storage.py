import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import StorageError


def empty_library() -> dict[str, Any]:
    return {"copies": {}, "readers": {}, "loans": []}


def _validate_library(data: object, path: Path) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise StorageError(f"数据文件 {path} 的顶层必须是 JSON 对象")

    copies = data.get("copies")
    readers = data.get("readers")
    loans = data.get("loans")
    if not isinstance(copies, dict):
        raise StorageError(f"数据文件 {path} 缺少有效的 copies 对象")
    if not isinstance(readers, dict):
        raise StorageError(f"数据文件 {path} 缺少有效的 readers 对象")
    if not isinstance(loans, list):
        raise StorageError(f"数据文件 {path} 缺少有效的 loans 数组")

    for copy_id, copy_data in copies.items():
        if not isinstance(copy_id, str) or not isinstance(copy_data, dict):
            raise StorageError(f"数据文件 {path} 包含无效的馆藏副本")
        if not isinstance(copy_data.get("title"), str) or not isinstance(
            copy_data.get("author"), str
        ):
            raise StorageError(f"数据文件 {path} 中副本 {copy_id} 的字段无效")

    for reader_id, reader_data in readers.items():
        if not isinstance(reader_id, str) or not isinstance(reader_data, dict):
            raise StorageError(f"数据文件 {path} 包含无效的读者")
        if not isinstance(reader_data.get("name"), str):
            raise StorageError(f"数据文件 {path} 中读者 {reader_id} 的字段无效")

    active_copies: set[str] = set()
    for loan in loans:
        if not isinstance(loan, dict):
            raise StorageError(f"数据文件 {path} 包含无效的借阅记录")
        copy_id = loan.get("copy_id")
        reader_id = loan.get("reader_id")
        borrowed_on = loan.get("borrowed_on")
        returned_on = loan.get("returned_on")
        if (
            not isinstance(copy_id, str)
            or copy_id not in copies
            or not isinstance(reader_id, str)
            or reader_id not in readers
            or not isinstance(borrowed_on, str)
            or (returned_on is not None and not isinstance(returned_on, str))
        ):
            raise StorageError(f"数据文件 {path} 包含字段无效的借阅记录")
        if returned_on is None:
            if copy_id in active_copies:
                raise StorageError(f"数据文件 {path} 中副本 {copy_id} 有多条未归还记录")
            active_copies.add(copy_id)

    return data


def load_library(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_library()

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageError(f"无法读取数据文件 {path}: {exc}") from exc
    return _validate_library(data, path)


def save_library(path: Path, data: dict[str, Any]) -> None:
    temporary_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            newline="\n",
        ) as handle:
            temporary_name = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except OSError as exc:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise StorageError(f"无法保存数据文件 {path}: {exc}") from exc

