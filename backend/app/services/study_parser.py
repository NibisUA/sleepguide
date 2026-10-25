"""Conservative, deterministic text-to-tracker parser. No material/answers are generated."""

import re
from datetime import date, timedelta

MONTHS = [
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
]
DATE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}(?:[./]\d{4})?|\d{1,2}\s+(?:"
    + "|".join(MONTHS)
    + r")(?:\s+\d{4})?)(?!\d)",
    re.I,
)
TOKEN = re.compile(r"([NН]\d+\.\d+|\d+)(?:\s*[–—-]\s*([NН]\d+\.\d+|\d+))?", re.I)


def parse_text(text, year=None):
    items, issues, reserve_dates = [], [], []
    name, deadline, start, total, reserve = "", None, None, None, 0
    current_day, group, weight, level = None, "", 1, None
    seen = set()
    has_schedule = False

    def issue(line, message):
        issues.append(dict(line=line, message=message))

    def read_date(value, line):
        match = DATE.match(value.strip())
        if not match:
            issue(line, "Не вдалося прочитати дату")
            return None, value
        token = match[0]
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
                result = date.fromisoformat(token)
            else:
                parts = (
                    token.lower().replace("/", ".").split(".")
                    if "." in token or "/" in token
                    else token.lower().split()
                )
                chosen_year = int(parts[2]) if len(parts) == 3 else year
                if chosen_year is None:
                    issue(line, "Дата без року: вибери рік і розпізнай повторно")
                    return None, value[match.end() :]
                month = int(parts[1]) if parts[1].isdigit() else MONTHS.index(parts[1]) + 1
                result = date(chosen_year, month, int(parts[0]))
            return result.isoformat(), value.strip()[match.end() :]
        except (ValueError, IndexError):
            issue(line, "Некоректна або неоднозначна дата")
            return None, value.strip()[match.end() :]

    for line_no, raw in enumerate(re.split(r"[\n;]", text.replace("\u00a0", " ")), 1):
        line = raw.strip().lstrip("•* ")
        if not line or re.fullmatch(r"[-_=]+", line):
            continue
        meta = re.match(r"(?:назва|предмет|ціль)\s*[:—-]\s*(.+)$", line, re.I)
        if meta:
            name = meta[1].strip()[:120]
            continue
        meta = re.match(r"(?:дедлайн|іспит|екзамен|здача)\s*[:—-]?\s*(.+)", line, re.I)
        if meta:
            deadline, _ = read_date(meta[1], line_no)
            continue
        meta = re.match(r"(?:початок|старт)\s*[:—-]?\s*(.+)", line, re.I)
        if meta:
            start, _ = read_date(meta[1], line_no)
            continue
        bare_total = re.fullmatch(r"(\d{1,4})\s+(?:питань|завдань)\.?", line, re.I)
        if bare_total:
            total = int(bare_total[1])
            continue
        meta = re.search(
            r"(?:усього|всього|загалом|кількість)\s*(?:питань|завдань)?\s*[:—-]?\s*(\d+)",
            line,
            re.I,
        )
        if meta:
            if len(meta[1]) > 4:
                issue(line_no, "Кількість надто велика: максимум 1000")
            else:
                total = int(meta[1])
            continue
        meta = re.search(r"(?:запас|резерв)\s*[:—-]?\s*(\d+)\s*(?:дн|день)", line, re.I)
        if meta:
            reserve = int(meta[1])
            continue
        if re.search(r"\(\s*Bara\s+\d+\s*\)", line, re.I):
            issue(line_no, "OCR змішав літери у слові «вага»: перевір складність групи")
            line = re.sub(r"(?<=\()\s*Bara(?=\s+\d+\s*\))", "вага", line, flags=re.I)
        header = re.match(
            r"(?:рівень|група)\s*([^:()]+?)(?:\s*\(\s*(?:складність|вага)\s*[:=]?\s*(\d+)\s*\))?\s*:\s*(.*)$",
            line,
            re.I,
        )
        if header:
            group = header[1].strip()
            weight = int(header[2] or 1) if len(header[2] or "1") <= 4 else 0
            if not 1 <= weight <= 100:
                issue(line_no, "Складність групи має бути від 1 до 100 — виправ вагу")
            level = group if group.isdigit() else None
            line = header[3].strip()
            if not line:
                continue
        date_match = DATE.match(line)
        date_tail = line[date_match.end() :].strip() if date_match else ""
        is_date_line = bool(
            date_match
            and (
                not date_tail
                or date_tail[0] in ":—–-"
                or re.match(r"питання|завдання|запас|резерв", date_tail, re.I)
                or any(month in date_match[0].lower() for month in MONTHS)
                or re.search(r"\d{4}", date_match[0])
            )
        )
        # Do not turn subitems such as 1.1 or extra flashcards into new questions.
        if re.match(r"\d+\.\d+(?!\d)[.)\s]", line) and not is_date_line:
            issue(line_no, "Підпункт пропущено; якщо це окреме питання, познач його N1.1")
            continue
        if is_date_line:
            current_day, line = read_date(line, line_no)
            has_schedule = True
            line = line.lstrip(" :—–-")
            if re.search(r"запас|резерв|повторення", line, re.I) and not re.search(
                r"питання|завдання|N\d", line, re.I
            ):
                if current_day:
                    reserve_dates.append(current_day)
                current_day = None
                continue
            if not line:
                continue
        line = re.sub(r"^(?:питання|завдання|номери|№)\s*[:—-]?\s*", "", line, flags=re.I).lstrip(
            "№ "
        )
        if re.match(r"\d+\.\d+", line):
            issue(line_no, "Підпункт не пораховано як окреме питання; потрібне явне позначення N")
            continue
        match = TOKEN.match(line)
        if not match:
            if not name and not items and not re.search(r"картк|відповід|тест", line, re.I):
                name = line[:120]
            else:
                issue(line_no, "Нерозпізнаний рядок: перевір або прибери його")
            continue
        position = 0
        while match:
            if len(match[1]) > 32 or (match[2] and len(match[2]) > 32):
                issue(line_no, "Номер надто довгий")
                break
            a, b = match[1].upper().replace("Н", "N"), match[2]
            b = b.upper().replace("Н", "N") if b else a
            prefix_a = (
                a.rsplit(".", 1)[0] + "." if a.startswith("N") else (f"N{level}." if level else "")
            )
            prefix_b = b.rsplit(".", 1)[0] + "." if b.startswith("N") else prefix_a
            low, high = int(a.split(".")[-1]), int(b.split(".")[-1])
            if prefix_a != prefix_b or low < 1 or high < low or high - low > 999:
                issue(line_no, "Діапазон різних груп, у зворотному порядку або надто великий")
                break
            tail = line[match.end() :]
            title = ""
            next_part = re.match(r"\s*[,і]\s*", tail)
            if not next_part and low == high:
                title = tail.lstrip(" .):—–-")[:160]
            for n in range(low, high + 1):
                label = prefix_a + str(n)
                if label in seen:
                    issue(line_no, f"Дублікат / перетин: {label}")
                    continue
                seen.add(label)
                items.append(
                    dict(
                        label=label,
                        title=title,
                        group=group or prefix_a.rstrip("."),
                        weight=weight,
                        scheduled_date=current_day,
                    )
                )
            if len(items) > 1000:
                issue(line_no, "Максимум 1000 питань у плані")
                items = items[:1000]
                break
            if not next_part:
                if low != high and tail.strip(" .):—–-"):
                    issue(line_no, "Зайвий текст після діапазону — перевір номери")
                break
            position = match.end() + next_part.end()
            match = TOKEN.match(line, position)
            if not match:
                issue(line_no, "Нерозпізнаний кінець переліку")
    if total is not None and total != len(items):
        issue(0, f"Заявлено {total}, розпізнано {len(items)} унікальних питань")
    prefixes = {}
    for row in items:
        prefix, number = row["label"].rsplit(".", 1) if "." in row["label"] else ("", row["label"])
        prefixes.setdefault(prefix, []).append(int(number))
    for prefix, numbers in prefixes.items():
        missing = (
            sorted(set(range(1, max(numbers) + 1)) - set(numbers)) if max(numbers) <= 2000 else []
        )
        if missing:
            issue(0, f"Пропуски {prefix or 'номерів'}: " + ", ".join(map(str, missing[:30])))
    scheduled = sorted(row["scheduled_date"] for row in items if row["scheduled_date"])
    if not start and scheduled:
        start = scheduled[0]
    if reserve_dates and not deadline:
        reserve = max(reserve, len(set(reserve_dates)))
        issue(0, "Вкажи дедлайн, щоб перевірити дати запасу")
    if deadline and reserve_dates:
        cursor, count = date.fromisoformat(deadline), 0
        while (cursor - timedelta(days=1)).isoformat() in reserve_dates:
            cursor -= timedelta(days=1)
            count += 1
        reserve = max(reserve, count)
        if count != len(set(reserve_dates)):
            issue(0, "Дні резерву не утворюють суцільний запас перед дедлайном")
    if not items:
        issue(0, "Не знайдено номерів питань")
    return dict(
        name=name,
        deadline=deadline,
        start_date=start,
        total=len(items),
        declared_total=total,
        reserve_days=reserve,
        reserve_dates=reserve_dates,
        items=items,
        preserve_schedule=has_schedule,
        issues=issues,
    )
