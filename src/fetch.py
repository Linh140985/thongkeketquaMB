__author__ = 'Khiem Doan'
__github__ = 'https://github.com/khiemdoan'
__email__ = 'doankhiem.crazy@gmail.com'

import json
import time as time_module
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from lottery import Lottery


MAX_RETRIES = 5
RETRY_DELAYS = [0, 8, 15, 25, 40]

DRAW_KEYS = [
    'special', 'prize1',
    'prize2_1', 'prize2_2',
    'prize3_1', 'prize3_2', 'prize3_3', 'prize3_4', 'prize3_5', 'prize3_6',
    'prize4_1', 'prize4_2', 'prize4_3', 'prize4_4',
    'prize5_1', 'prize5_2', 'prize5_3', 'prize5_4', 'prize5_5', 'prize5_6',
    'prize6_1', 'prize6_2', 'prize6_3',
    'prize7_1', 'prize7_2', 'prize7_3', 'prize7_4',
]


def target_date_vietnam():
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    target = now.date()
    if now.time() < time(18, 35):
        target -= timedelta(days=1)
    return target


def fetch_with_retry(lottery: Lottery, selected_date) -> None:
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        delay = RETRY_DELAYS[attempt - 1]
        if delay:
            print(f'Waiting {delay}s before retry {attempt}/{MAX_RETRIES}...')
            time_module.sleep(delay)

        print(f'Fetching: {selected_date} (attempt {attempt}/{MAX_RETRIES})')
        try:
            lottery.fetch(selected_date)
            # Lottery.fetch only inserts a date after all prize groups were parsed
            # and the Result object was created successfully.
            if selected_date in lottery._data:
                print(f'Fetched OK: {selected_date}')
                return
            last_error = RuntimeError('source returned no complete result')
        except Exception as exc:
            last_error = exc
            print(f'Fetch failed: {type(exc).__name__}: {exc}')

    raise RuntimeError(
        f'Cannot fetch complete XSMB result for {selected_date} after '
        f'{MAX_RETRIES} attempts. Last error: {last_error}'
    )


def validate_output(expected_date) -> None:
    with open('data/xsmb-2-digits.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    expected = expected_date.isoformat()
    matches = [row for row in data if str(row.get('date', ''))[:10] == expected]
    if len(matches) != 1:
        raise RuntimeError(
            f'Validation failed: expected exactly one row for {expected}, '
            f'found {len(matches)}.'
        )

    row = matches[0]
    missing = [key for key in DRAW_KEYS if key not in row]
    if missing:
        raise RuntimeError(f'Validation failed for {expected}: missing fields {missing}')

    values = []
    for key in DRAW_KEYS:
        try:
            value = int(row[key])
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f'Validation failed for {expected}: {key} is not numeric.'
            ) from exc
        if not 0 <= value <= 99:
            raise RuntimeError(
                f'Validation failed for {expected}: {key}={value} is outside 00-99.'
            )
        values.append(value)

    if len(values) != 27:
        raise RuntimeError(
            f'Validation failed for {expected}: expected 27 prize values, got {len(values)}.'
        )

    latest = max(str(r.get('date', ''))[:10] for r in data if r.get('date'))
    if latest != expected:
        raise RuntimeError(
            f'Validation failed: latest data date is {latest}, expected {expected}.'
        )

    print(f'VALIDATION OK: {expected} has exactly 27 two-digit prize values.')


if __name__ == '__main__':
    lottery = Lottery()
    lottery.load()

    begin_date = lottery.get_last_date()
    target_date = target_date_vietnam()

    print(f'Current latest date: {begin_date}')
    print(f'Target date: {target_date}')

    if begin_date >= target_date:
        print('Data is already up to date. Nothing to fetch.')
        validate_output(begin_date)
        raise SystemExit(0)

    delta = (target_date - begin_date).days
    for i in range(1, delta + 1):
        selected_date = begin_date + timedelta(days=i)
        fetch_with_retry(lottery, selected_date)

    lottery.generate_dataframes()
    lottery.dump()
    validate_output(target_date)
