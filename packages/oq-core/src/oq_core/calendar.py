"""NSE trading calendar.

This module implements a minimal-but-correct NSE equity trading calendar:

* Mon-Fri are trading days.
* Saturday and Sunday are non-trading days.
* A curated set of NSE trading holidays is loaded from
  :data:`HOLIDAYS_BY_YEAR`.
* Muhurat (Diwali) sessions are special trading days where the date would
  otherwise be a holiday or where only an evening session is open.

The calendar API is intentionally small and deterministic so that ``oq-data``
and ``oq-backtest`` can rely on it without pulling pandas at import time.

Holiday lists are maintained by year. They are best-effort and should be
verified against the NSE annual circular for any production usage.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)


@dataclass(frozen=True, slots=True)
class MuhuratSession:
    """A Diwali muhurat trading session (evening, typically ~1 hour)."""

    session_date: date
    open_time: time
    close_time: time


# NSE trading holidays. Source: NSE annual holiday circulars.
# Only includes fully-closed equity trading days (not settlement holidays).
# This list is best-effort; consumers should verify against the NSE circular.
HOLIDAYS_BY_YEAR: dict[int, frozenset[date]] = {
    2023: frozenset(
        {
            date(2023, 1, 26),  # Republic Day
            date(2023, 3, 7),  # Holi
            date(2023, 3, 30),  # Ram Navami
            date(2023, 4, 4),  # Mahavir Jayanti
            date(2023, 4, 7),  # Good Friday
            date(2023, 4, 14),  # Dr. Ambedkar Jayanti
            date(2023, 5, 1),  # Maharashtra Day
            date(2023, 6, 28),  # Bakri Id
            date(2023, 8, 15),  # Independence Day
            date(2023, 9, 19),  # Ganesh Chaturthi
            date(2023, 10, 2),  # Gandhi Jayanti
            date(2023, 10, 24),  # Dussehra
            date(2023, 11, 14),  # Diwali Balipratipada
            date(2023, 11, 27),  # Guru Nanak Jayanti
            date(2023, 12, 25),  # Christmas
        }
    ),
    2024: frozenset(
        {
            date(2024, 1, 26),  # Republic Day
            date(2024, 3, 8),  # Mahashivratri
            date(2024, 3, 25),  # Holi
            date(2024, 3, 29),  # Good Friday
            date(2024, 4, 11),  # Id-Ul-Fitr
            date(2024, 4, 17),  # Ram Navami
            date(2024, 5, 1),  # Maharashtra Day
            date(2024, 5, 20),  # General Elections (Mumbai)
            date(2024, 6, 17),  # Bakri Id
            date(2024, 7, 17),  # Muharram
            date(2024, 8, 15),  # Independence Day
            date(2024, 10, 2),  # Gandhi Jayanti
            date(2024, 11, 1),  # Diwali Laxmi Pujan (full holiday; muhurat session in evening)
            date(2024, 11, 15),  # Guru Nanak Jayanti
            date(2024, 12, 25),  # Christmas
        }
    ),
    2025: frozenset(
        {
            date(2025, 2, 26),  # Mahashivratri
            date(2025, 3, 14),  # Holi
            date(2025, 3, 31),  # Id-Ul-Fitr
            date(2025, 4, 10),  # Mahavir Jayanti
            date(2025, 4, 14),  # Dr. Ambedkar Jayanti
            date(2025, 4, 18),  # Good Friday
            date(2025, 5, 1),  # Maharashtra Day
            date(2025, 8, 15),  # Independence Day
            date(2025, 8, 27),  # Ganesh Chaturthi
            date(2025, 10, 2),  # Gandhi Jayanti / Dussehra
            date(2025, 10, 21),  # Diwali Laxmi Pujan (muhurat session in evening)
            date(2025, 10, 22),  # Diwali Balipratipada
            date(2025, 11, 5),  # Guru Nanak Jayanti
            date(2025, 12, 25),  # Christmas
        }
    ),
}


# Muhurat (Diwali) trading sessions. These are evening sessions on what would
# otherwise be a non-trading day.
MUHURAT_SESSIONS: tuple[MuhuratSession, ...] = (
    MuhuratSession(date(2023, 11, 12), time(18, 15), time(19, 15)),
    MuhuratSession(date(2024, 11, 1), time(18, 0), time(19, 0)),
    MuhuratSession(date(2025, 10, 21), time(13, 45), time(14, 45)),
)


class TradingCalendar:
    """NSE equity trading calendar.

    Parameters
    ----------
    holidays:
        Optional override mapping of year to holiday set. Defaults to the
        bundled :data:`HOLIDAYS_BY_YEAR`.
    muhurat:
        Optional override of muhurat sessions. Defaults to
        :data:`MUHURAT_SESSIONS`.
    """

    def __init__(
        self,
        holidays: dict[int, frozenset[date]] | None = None,
        muhurat: tuple[MuhuratSession, ...] | None = None,
    ) -> None:
        self._holidays: dict[int, frozenset[date]] = (
            dict(holidays) if holidays is not None else dict(HOLIDAYS_BY_YEAR)
        )
        self._muhurat: dict[date, MuhuratSession] = {
            session.session_date: session
            for session in (muhurat if muhurat is not None else MUHURAT_SESSIONS)
        }

    def is_weekend(self, day: date) -> bool:
        return day.weekday() >= 5

    def is_holiday(self, day: date) -> bool:
        """True if ``day`` is on the published NSE holiday list."""
        return day in self._holidays.get(day.year, frozenset())

    def muhurat_session(self, day: date) -> MuhuratSession | None:
        """Return the muhurat session for ``day``, if any."""
        return self._muhurat.get(day)

    def is_session(self, day: date) -> bool:
        """True if regular trading happens on ``day`` (excludes muhurat-only days)."""
        if self.is_weekend(day):
            return False
        return not self.is_holiday(day)

    def is_trading_day(self, day: date) -> bool:
        """True if any trading occurs on ``day`` (regular session OR muhurat)."""
        if self.is_session(day):
            return True
        return day in self._muhurat

    def next_session(self, day: date) -> date:
        """Smallest ``d > day`` that is a regular session."""
        candidate = day + timedelta(days=1)
        while not self.is_session(candidate):
            candidate += timedelta(days=1)
        return candidate

    def previous_session(self, day: date) -> date:
        """Largest ``d < day`` that is a regular session."""
        candidate = day - timedelta(days=1)
        while not self.is_session(candidate):
            candidate -= timedelta(days=1)
        return candidate

    def sessions(self, start: date, end: date) -> Iterator[date]:
        """Yield regular trading sessions in ``[start, end]`` inclusive."""
        if end < start:
            return
        current = start
        while current <= end:
            if self.is_session(current):
                yield current
            current += timedelta(days=1)

    def session_count(self, start: date, end: date) -> int:
        """Number of regular trading sessions in ``[start, end]`` inclusive."""
        return sum(1 for _ in self.sessions(start, end))

    def is_market_open(self, when: datetime) -> bool:
        """True if the regular cash market is open at ``when`` (naive local IST)."""
        day = when.date()
        if not self.is_session(day):
            return False
        return NSE_OPEN <= when.time() <= NSE_CLOSE
