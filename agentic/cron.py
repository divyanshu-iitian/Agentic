"""A small five-field cron parser: minute hour day-of-month month day-of-week.

Supports *, lists (1,15), ranges (1-5), and steps (*/10, 0-30/5). Day of
week is 0-6 with Sunday as 0 (7 is accepted as Sunday too). As in standard
cron, when both day fields are restricted a time matches either of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

FIELDS = (("minute", 0, 59), ("hour", 0, 23), ("day", 1, 31), ("month", 1, 12), ("weekday", 0, 7))


def _parse_field(expression: str, low: int, high: int) -> frozenset[int]:
    values: set[int] = set()
    for part in expression.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            step = int(step_text)
            if step < 1:
                raise ValueError("cron step must be at least 1")
        if part == "*":
            start, end = low, high
        elif "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
        else:
            start = int(part)
            end = high if step > 1 else start
        if not (low <= start <= high and low <= end <= high and start <= end):
            raise ValueError(f"cron value out of range {low}-{high}: {part}")
        values.update(range(start, end + 1, step))
    return frozenset(values)


@dataclass(frozen=True)
class CronSchedule:
    expression: str
    minutes: frozenset[int]
    hours: frozenset[int]
    days: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]
    day_restricted: bool
    weekday_restricted: bool

    @classmethod
    def parse(cls, expression: str) -> CronSchedule:
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError("cron expressions need five fields: minute hour day month weekday")
        try:
            parsed = [
                _parse_field(part, low, high)
                for part, (_, low, high) in zip(parts, FIELDS, strict=True)
            ]
        except ValueError as exc:
            raise ValueError(f"invalid cron expression {expression!r}: {exc}") from exc
        weekdays = frozenset(0 if day == 7 else day for day in parsed[4])
        return cls(
            expression,
            parsed[0],
            parsed[1],
            parsed[2],
            parsed[3],
            weekdays,
            parts[2] != "*",
            parts[4] != "*",
        )

    def _day_matches(self, moment: datetime) -> bool:
        day_ok = moment.day in self.days
        weekday_ok = (moment.isoweekday() % 7) in self.weekdays
        if self.day_restricted and self.weekday_restricted:
            return day_ok or weekday_ok
        return day_ok and weekday_ok

    def next_after(self, moment: datetime) -> datetime:
        """The first matching minute strictly after `moment` (local time)."""
        current = moment.replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = current + timedelta(days=366 * 5)
        while current < limit:
            if current.month not in self.months:
                year = current.year + (current.month == 12)
                month = 1 if current.month == 12 else current.month + 1
                current = current.replace(year=year, month=month, day=1, hour=0, minute=0)
                continue
            if not self._day_matches(current):
                current = (current + timedelta(days=1)).replace(hour=0, minute=0)
                continue
            if current.hour not in self.hours:
                current = (current + timedelta(hours=1)).replace(minute=0)
                continue
            if current.minute not in self.minutes:
                current += timedelta(minutes=1)
                continue
            return current
        raise ValueError(f"cron expression {self.expression!r} never matches")
