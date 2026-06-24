# `oq-core`

Shared primitives. Lean by design — no heavy dependencies.

## `Instrument`

```python
from oq_core import Instrument, Segment

i = Instrument(symbol="RELIANCE", isin="INE002A01018")
str(i)              # "NSE:EQ:RELIANCE"
i.segment           # Segment.EQ
```

Fields:

| Field    | Type      | Default       |
| -------- | --------- | ------------- |
| symbol   | `str`     | required      |
| isin     | `str`     | required      |
| exchange | `str`     | `"NSE"`       |
| segment  | `Segment` | `Segment.EQ`  |
| lot_size | `int`     | `1`           |

## `TradingCalendar`

```python
from datetime import date
from oq_core import TradingCalendar

cal = TradingCalendar()
cal.is_session(date(2024, 1, 26))      # False — Republic Day
cal.next_session(date(2024, 8, 14))    # date(2024, 8, 16)
cal.sessions_between(start, end)       # list[date]
cal.is_muhurat(date(2024, 11, 1))      # True if Diwali muhurat session
```

Loaded holidays cover NSE EQ; special sessions (muhurat, exceptional
half-days) are versioned in the package.
