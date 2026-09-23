from copy import deepcopy
from datetime import date
from typing import Any

from .errors import ValidationError
from .isbn import compact_isbn, normalize_isbn

MAX_ACTIVE_LOANS = 5


def _required(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label}不能为空")
    return cleaned


def parse_date(value: str, label: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{label}必须使用 YYYY-MM-DD 格式") from exc
    if parsed.isoformat() != value:
        raise ValidationError(f"{label}必须使用 YYYY-MM-DD 格式")
    return value


def add_copy(
    data: dict[str, Any],
    copy_id: str,
    title: str,
    author: str,
    isbn: str | None = None,
) -> dict[str, Any]:
    copy_id = _required(copy_id, "副本编号")
    title = _required(title, "书名")
    author = _required(author, "作者")
    if copy_id in data["copies"]:
        raise ValidationError(f"副本 {copy_id} 已存在")
    normalized_isbn = normalize_isbn(isbn) if isbn is not None else None

    updated = deepcopy(data)
    updated["copies"][copy_id] = {
        "title": title,
        "author": author,
        "isbn": normalized_isbn,
    }
    return updated


def register_reader(
    data: dict[str, Any], reader_id: str, name: str
) -> dict[str, Any]:
    reader_id = _required(reader_id, "读者编号")
    name = _required(name, "姓名")
    if reader_id in data["readers"]:
        raise ValidationError(f"读者 {reader_id} 已存在")

    updated = deepcopy(data)
    updated["readers"][reader_id] = {"name": name}
    return updated


def active_loan_for_copy(
    data: dict[str, Any], copy_id: str
) -> dict[str, Any] | None:
    return next(
        (
            loan
            for loan in data["loans"]
            if loan["copy_id"] == copy_id and loan["returned_on"] is None
        ),
        None,
    )


def borrow_copy(
    data: dict[str, Any], copy_id: str, reader_id: str, borrowed_on: str
) -> dict[str, Any]:
    borrowed_on = parse_date(borrowed_on, "借阅日期")
    if copy_id not in data["copies"]:
        raise ValidationError(f"副本 {copy_id} 不存在")
    if reader_id not in data["readers"]:
        raise ValidationError(f"读者 {reader_id} 不存在")
    if active_loan_for_copy(data, copy_id) is not None:
        raise ValidationError(f"副本 {copy_id} 当前已借出")

    active_count = sum(
        1
        for loan in data["loans"]
        if loan["reader_id"] == reader_id and loan["returned_on"] is None
    )
    if active_count >= MAX_ACTIVE_LOANS:
        raise ValidationError(f"读者 {reader_id} 已达到同时借阅 {MAX_ACTIVE_LOANS} 本的上限")

    updated = deepcopy(data)
    updated["loans"].append(
        {
            "copy_id": copy_id,
            "reader_id": reader_id,
            "borrowed_on": borrowed_on,
            "returned_on": None,
        }
    )
    return updated


def return_copy(
    data: dict[str, Any], copy_id: str, returned_on: str
) -> dict[str, Any]:
    returned_on = parse_date(returned_on, "归还日期")
    if copy_id not in data["copies"]:
        raise ValidationError(f"副本 {copy_id} 不存在")
    loan = active_loan_for_copy(data, copy_id)
    if loan is None:
        raise ValidationError(f"副本 {copy_id} 当前未借出")
    if returned_on < loan["borrowed_on"]:
        raise ValidationError("归还日期不能早于借阅日期")

    updated = deepcopy(data)
    updated_loan = active_loan_for_copy(updated, copy_id)
    assert updated_loan is not None
    updated_loan["returned_on"] = returned_on
    return updated


def list_copies(data: dict[str, Any], status: str) -> list[dict[str, str]]:
    rows = []
    for copy_id, copy_data in sorted(data["copies"].items()):
        loan = active_loan_for_copy(data, copy_id)
        copy_status = "borrowed" if loan else "available"
        if status != "all" and status != copy_status:
            continue
        rows.append(
            {
                "copy_id": copy_id,
                "title": copy_data["title"],
                "author": copy_data["author"],
                "isbn": copy_data.get("isbn") or "-",
                "status": copy_status,
                "reader_id": loan["reader_id"] if loan else "-",
                "borrowed_on": loan["borrowed_on"] if loan else "-",
            }
        )
    return rows


def search_copies(
    data: dict[str, Any], query: str, field: str
) -> list[dict[str, str]]:
    query = _required(query, "搜索词")
    text_query = query.casefold()
    isbn_query = compact_isbn(query)
    if field == "isbn" and not isbn_query:
        raise ValidationError("ISBN 搜索词不能为空")
    rows = list_copies(data, "all")
    return [
        row
        for row in rows
        if (field in ("all", "title") and text_query in row["title"].casefold())
        or (field in ("all", "author") and text_query in row["author"].casefold())
        or (
            field in ("all", "isbn")
            and bool(isbn_query)
            and row["isbn"] != "-"
            and isbn_query in row["isbn"]
        )
    ]


def loan_history(
    data: dict[str, Any], reader_id: str | None, status: str
) -> list[dict[str, str]]:
    if reader_id is not None and reader_id not in data["readers"]:
        raise ValidationError(f"读者 {reader_id} 不存在")
    if status not in ("all", "active", "returned"):
        raise ValidationError(f"未知借阅状态：{status}")

    rows = []
    for loan in data["loans"]:
        if reader_id is not None and loan["reader_id"] != reader_id:
            continue
        is_active = loan["returned_on"] is None
        if status == "active" and not is_active:
            continue
        if status == "returned" and is_active:
            continue
        rows.append(
            {
                "copy_id": loan["copy_id"],
                "reader_id": loan["reader_id"],
                "borrowed_on": loan["borrowed_on"],
                "returned_on": loan["returned_on"] or "-",
            }
        )
    rows.sort(key=lambda row: row["borrowed_on"])
    return rows
