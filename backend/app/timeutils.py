from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def ist_today() -> date:
    """The exam-day boundary is always IST midnight-to-midnight, regardless
    of what timezone the server/container the app happens to run on is set
    to — date.today() would silently follow the server's local clock."""
    return datetime.now(IST).date()
