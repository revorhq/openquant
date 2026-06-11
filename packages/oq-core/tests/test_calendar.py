"""Tests for oq_core.calendar."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest
from oq_core import TradingCalendar
from oq_core.calendar import MUHURAT_SESSIONS, MuhuratSession


@pytest.fixture
def cal() -> TradingCalendar:
    return TradingCalendar()


class TestWeekends:
    def test_saturday_is_weekend(self, cal: TradingCalendar) -> None:
        assert cal.is_weekend(date(2024, 6, 8))  # Saturday
        assert not cal.is_session(date(2024, 6, 8))

    def test_sunday_is_weekend(self, cal: TradingCalendar) -> None:
        assert cal.is_weekend(date(2024, 6, 9))  # Sunday
        assert not cal.is_session(date(2024, 6, 9))

    def test_weekday_not_weekend(self, cal: TradingCalendar) -> None:
        assert not cal.is_weekend(date(2024, 6, 10))  # Monday


class TestHolidays:
    def test_republic_day_2024(self, cal: TradingCalendar) -> None:
        assert cal.is_holiday(date(2024, 1, 26))
        assert not cal.is_session(date(2024, 1, 26))

    def test_christmas_2025(self, cal: TradingCalendar) -> None:
        assert cal.is_holiday(date(2025, 12, 25))

    def test_regular_weekday_not_holiday(self, cal: TradingCalendar) -> None:
        assert not cal.is_holiday(date(2024, 6, 10))
        assert cal.is_session(date(2024, 6, 10))

    def test_unknown_year_no_holidays(self, cal: TradingCalendar) -> None:
        assert not cal.is_holiday(date(2099, 1, 26))


class TestMuhurat:
    def test_known_muhurat_dates_present(self) -> None:
        dates = {s.session_date for s in MUHURAT_SESSIONS}
        assert date(2024, 11, 1) in dates
        assert date(2025, 10, 21) in dates

    def test_muhurat_lookup(self, cal: TradingCalendar) -> None:
        s = cal.muhurat_session(date(2024, 11, 1))
        assert s is not None
        assert s.open_time < s.close_time

    def test_muhurat_only_day_is_trading_not_session(self) -> None:
        # 2024-11-01 is a Diwali holiday but has a muhurat session
        cal = TradingCalendar()
        d = date(2024, 11, 1)
        assert cal.is_holiday(d)
        assert not cal.is_session(d)
        assert cal.is_trading_day(d)


class TestNavigation:
    def test_next_session_skips_weekend(self, cal: TradingCalendar) -> None:
        # Friday 2024-06-07 -> next session Monday 2024-06-10
        assert cal.next_session(date(2024, 6, 7)) == date(2024, 6, 10)

    def test_previous_session_skips_weekend(self, cal: TradingCalendar) -> None:
        # Monday 2024-06-10 -> previous session Friday 2024-06-07
        assert cal.previous_session(date(2024, 6, 10)) == date(2024, 6, 7)

    def test_next_session_skips_holiday(self, cal: TradingCalendar) -> None:
        # 2024-08-15 (Thu) is Independence Day -> next session 2024-08-16 (Fri)
        assert cal.next_session(date(2024, 8, 14)) == date(2024, 8, 16)


class TestSessionRange:
    def test_sessions_in_week(self, cal: TradingCalendar) -> None:
        # Mon 2024-06-10 to Sun 2024-06-16: 5 sessions
        days = list(cal.sessions(date(2024, 6, 10), date(2024, 6, 16)))
        assert len(days) == 5
        assert days[0] == date(2024, 6, 10)
        assert days[-1] == date(2024, 6, 14)

    def test_sessions_empty_when_end_before_start(self, cal: TradingCalendar) -> None:
        assert list(cal.sessions(date(2024, 6, 10), date(2024, 6, 5))) == []

    def test_session_count_around_holiday(self, cal: TradingCalendar) -> None:
        # Week of Independence Day 2024 (Thu Aug 15): Mon-Fri minus Thu = 4
        assert cal.session_count(date(2024, 8, 12), date(2024, 8, 16)) == 4


class TestMarketHours:
    def test_open_at_open_time(self, cal: TradingCalendar) -> None:
        assert cal.is_market_open(datetime(2024, 6, 10, 9, 15))

    def test_open_mid_session(self, cal: TradingCalendar) -> None:
        assert cal.is_market_open(datetime(2024, 6, 10, 12, 0))

    def test_closed_before_open(self, cal: TradingCalendar) -> None:
        assert not cal.is_market_open(datetime(2024, 6, 10, 9, 0))

    def test_closed_after_close(self, cal: TradingCalendar) -> None:
        assert not cal.is_market_open(datetime(2024, 6, 10, 15, 31))

    def test_closed_on_weekend(self, cal: TradingCalendar) -> None:
        assert not cal.is_market_open(datetime(2024, 6, 8, 12, 0))

    def test_closed_on_holiday(self, cal: TradingCalendar) -> None:
        assert not cal.is_market_open(datetime(2024, 1, 26, 12, 0))


class TestOverrides:
    def test_custom_holidays(self) -> None:
        custom = {2030: frozenset({date(2030, 1, 1)})}
        cal = TradingCalendar(holidays=custom)
        assert cal.is_holiday(date(2030, 1, 1))
        assert not cal.is_holiday(date(2024, 1, 26))

    def test_custom_muhurat(self) -> None:
        s = MuhuratSession(date(2030, 11, 5), time(18, 0), time(19, 0))
        cal = TradingCalendar(muhurat=(s,))
        assert cal.muhurat_session(date(2030, 11, 5)) == s
