# 本地图书借阅管理 CLI

一个面向小型社区图书室的 Python 3.11+ 单机命令行工具。它管理馆藏副本、读者及借还记录，数据保存在本地 JSON 文件中，仅使用 Python 标准库。

## 安装与运行

无需安装第三方依赖。确认已安装 Python 3.11 或更高版本，然后在项目根目录运行：

```powershell
python -m library_cli --help
```

全局选项 `--data-file PATH` 必须放在子命令之前。默认数据文件为 `data/library.json`；首次执行写操作时会自动创建目录和文件。

## 命令示例

```powershell
# 添加馆藏副本
python -m library_cli add-copy C001 "海边的卡夫卡" "村上春树"

# 注册读者
python -m library_cli register-reader R001 "小林"

# 借书与归还（日期必须为 YYYY-MM-DD）
python -m library_cli borrow C001 R001 2026-09-23
python -m library_cli return C001 2026-09-30

# 列出全部、可借或已借出的馆藏
python -m library_cli list
python -m library_cli list --status available
python -m library_cli list --status borrowed

# 同时搜索书名和作者，或限定字段
python -m library_cli search "卡夫卡"
python -m library_cli search "村上" --field author
python -m library_cli search "海边" --field title

# 使用另一个数据文件
python -m library_cli --data-file C:\library\branch-a.json list
```

成功的写操作会输出一行确认信息。例如：

```text
已借出副本 C001 给读者 R001，日期：2026-09-23
```

列表和搜索结果适合直接阅读：

```text
C001 | 海边的卡夫卡 | 村上春树 | 状态: 已借出 | 读者: R001 | 借阅日期: 2026-09-23
```

失败信息写入标准错误，进程返回非零退出码：

```text
错误：副本 C001 当前已借出
```

## 业务限制与数据安全

- 副本编号和读者编号各自唯一。
- 同一副本同一时间只能借给一位读者。
- 每位读者最多同时借阅 5 本。
- 借阅和归还日期严格使用 `YYYY-MM-DD`；归还日期不能早于借阅日期。
- 命令会在全部校验通过后才更新数据，并通过同目录临时文件原子替换 JSON；业务失败不会改动已有数据。
- 本工具面向单进程使用，不提供多个进程同时写同一数据文件的锁定机制。

JSON 顶层包含 `copies`、`readers` 和 `loans`。UTF-8 文本以缩进格式保存，便于备份和人工检查。

## 测试

```powershell
python -m unittest discover -v
```

