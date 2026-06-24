from __future__ import annotations

from datetime import date

from oq_data import universes as un
from oq_data.config import DataPaths


def _seed(tmp_paths: DataPaths) -> None:
    un.add_entries(
        [
            un.UniverseEntry("NIFTY50", "RELIANCE", "INE002A01018", date(2020, 1, 1), None),
            un.UniverseEntry("NIFTY50", "TCS", "INE467B01029", date(2020, 1, 1), None),
            un.UniverseEntry(
                "NIFTY50", "HDFC", "INE001A01036", date(2020, 1, 1), date(2023, 7, 13)
            ),
            un.UniverseEntry("NIFTY50", "HDFCBANK", "INE040A01034", date(2023, 7, 13), None),
        ],
        paths=tmp_paths,
    )


def test_members_as_of_pre_merger(tmp_paths: DataPaths) -> None:
    _seed(tmp_paths)
    members = un.members_as_of("NIFTY50", date(2023, 7, 12), paths=tmp_paths)
    assert set(members["symbol"]) == {"RELIANCE", "TCS", "HDFC"}


def test_members_as_of_post_merger(tmp_paths: DataPaths) -> None:
    _seed(tmp_paths)
    members = un.members_as_of("NIFTY50", date(2023, 7, 14), paths=tmp_paths)
    assert set(members["symbol"]) == {"RELIANCE", "TCS", "HDFCBANK"}


def test_members_as_of_on_exclude_date_excludes(tmp_paths: DataPaths) -> None:
    _seed(tmp_paths)
    members = un.members_as_of("NIFTY50", date(2023, 7, 13), paths=tmp_paths)
    assert "HDFC" not in set(members["symbol"])
    assert "HDFCBANK" in set(members["symbol"])


def test_membership_history(tmp_paths: DataPaths) -> None:
    _seed(tmp_paths)
    hist = un.membership_history("NIFTY50", paths=tmp_paths)
    assert len(hist) == 4


def test_empty_returns_empty(tmp_paths: DataPaths) -> None:
    assert un.members_as_of("NIFTY50", date(2024, 1, 1), paths=tmp_paths).empty
