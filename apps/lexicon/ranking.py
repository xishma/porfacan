import math
from datetime import datetime
from zoneinfo import ZoneInfo


EPOCH = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def hot_score(upvotes: int, downvotes: int, created_at: datetime) -> float:
    score = upvotes - downvotes
    order = math.log10(max(abs(score), 1))
    sign = 1 if score > 0 else -1 if score < 0 else 0
    seconds = (created_at.astimezone(ZoneInfo("UTC")) - EPOCH).total_seconds()
    return round(order + sign * seconds / 45000, 7)
