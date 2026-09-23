import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from .csv_import import import_copies
from .errors import LibraryError
from .service import (
    add_copy,
    borrow_copy,
    list_copies,
    loan_history,
    register_reader,
    return_copy,
    search_copies,
)
from .storage import load_library, save_library

DEFAULT_DATA_FILE = Path("data/library.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="本地图书借阅管理")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="JSON 数据文件路径（默认：data/library.json）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add-copy", help="添加馆藏副本")
    add_parser.add_argument("copy_id", help="副本编号")
    add_parser.add_argument("title", help="书名")
    add_parser.add_argument("author", help="作者")
    add_parser.add_argument("--isbn", help="可选的 ISBN-10 或 ISBN-13")

    reader_parser = subparsers.add_parser("register-reader", help="注册读者")
    reader_parser.add_argument("reader_id", help="读者编号")
    reader_parser.add_argument("name", help="姓名")

    borrow_parser = subparsers.add_parser("borrow", help="借出副本")
    borrow_parser.add_argument("copy_id", help="副本编号")
    borrow_parser.add_argument("reader_id", help="读者编号")
    borrow_parser.add_argument("date", help="借阅日期，YYYY-MM-DD")

    return_parser = subparsers.add_parser("return", help="归还副本")
    return_parser.add_argument("copy_id", help="副本编号")
    return_parser.add_argument("date", help="归还日期，YYYY-MM-DD")

    list_parser = subparsers.add_parser("list", help="按状态列出馆藏")
    list_parser.add_argument(
        "--status",
        choices=("all", "available", "borrowed"),
        default="all",
        help="馆藏状态（默认：all）",
    )

    search_parser = subparsers.add_parser("search", help="按书名、作者或 ISBN 搜索")
    search_parser.add_argument("query", help="搜索词，不区分大小写")
    search_parser.add_argument(
        "--field",
        choices=("all", "title", "author", "isbn"),
        default="all",
        help="搜索字段（默认：all）",
    )

    import_parser = subparsers.add_parser("import-copies", help="从 CSV 批量导入馆藏")
    import_parser.add_argument("csv_path", type=Path, help="UTF-8 CSV 文件路径")
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅完成全部校验，不写入数据文件",
    )

    history_parser = subparsers.add_parser("history", help="查询借阅历史")
    history_parser.add_argument("--reader", help="仅显示指定读者的记录")
    history_parser.add_argument(
        "--status",
        choices=("all", "active", "returned"),
        default="all",
        help="借阅状态（默认：all）",
    )
    return parser


def _print_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("没有匹配的馆藏。")
        return
    for row in rows:
        details = (
            f"{row['copy_id']} | {row['title']} | {row['author']} | "
            f"ISBN: {row['isbn']} | "
            f"状态: {'已借出' if row['status'] == 'borrowed' else '可借'}"
        )
        if row["status"] == "borrowed":
            details += f" | 读者: {row['reader_id']} | 借阅日期: {row['borrowed_on']}"
        print(details)


def _print_history(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("没有匹配的借阅记录。")
        return
    for row in rows:
        print(
            f"副本: {row['copy_id']} | 读者: {row['reader_id']} | "
            f"借阅日期: {row['borrowed_on']} | 归还日期: {row['returned_on']}"
        )


def run_write_command(
    args: argparse.Namespace, data: dict[str, Any]
) -> tuple[dict[str, Any], list[str], bool]:
    if args.command == "add-copy":
        return (
            add_copy(data, args.copy_id, args.title, args.author, args.isbn),
            [f"已添加副本 {args.copy_id}：{args.title} / {args.author}"],
            True,
        )
    if args.command == "register-reader":
        return (
            register_reader(data, args.reader_id, args.name),
            [f"已注册读者 {args.reader_id}：{args.name}"],
            True,
        )
    if args.command == "borrow":
        return (
            borrow_copy(data, args.copy_id, args.reader_id, args.date),
            [f"已借出副本 {args.copy_id} 给读者 {args.reader_id}，日期：{args.date}"],
            True,
        )
    if args.command == "return":
        return (
            return_copy(data, args.copy_id, args.date),
            [f"已归还副本 {args.copy_id}，日期：{args.date}"],
            True,
        )
    if args.command == "import-copies":
        updated, imported = import_copies(data, args.csv_path)
        messages = [
            f"CSV 第 {line_number} 行：副本 {copy_id} 校验通过"
            for line_number, copy_id in imported
        ]
        if args.dry_run:
            messages.append(f"试运行完成：将导入 {len(imported)} 个馆藏副本，未写入数据")
        else:
            messages.append(f"已导入 {len(imported)} 个馆藏副本")
        return updated, messages, not args.dry_run
    raise AssertionError(f"unknown write command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = load_library(args.data_file)
        if args.command == "list":
            _print_rows(list_copies(data, args.status))
        elif args.command == "search":
            _print_rows(search_copies(data, args.query, args.field))
        elif args.command == "history":
            _print_history(loan_history(data, args.reader, args.status))
        else:
            updated, messages, should_save = run_write_command(args, data)
            if should_save:
                save_library(args.data_file, updated)
            for message in messages:
                print(message)
        return 0
    except LibraryError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
