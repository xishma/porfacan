from datetime import datetime
from zoneinfo import ZoneInfo

from apps.lexicon.ranking import hot_score


def test_hot_score_positive_score():
    created_at = datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC"))
    score = hot_score(upvotes=12, downvotes=3, created_at=created_at)
    assert score > 0


def test_hot_score_zero_votes():
    created_at = datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC"))
    score = hot_score(upvotes=0, downvotes=0, created_at=created_at)
    assert isinstance(score, float)


def test_hot_score_negative_score():
    created_at = datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC"))
    score = hot_score(upvotes=2, downvotes=7, created_at=created_at)
    assert score < 0
