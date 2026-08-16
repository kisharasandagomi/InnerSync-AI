"""VADER and TextBlob sentiment scoring — descriptive only, not model inputs.

Reported alongside Experiment B to characterise the Dreaddit text
(does a general-purpose sentiment lexicon separate the two classes at all,
roughly, before any supervised model is fit), not as a third ablation
condition. Neither score is used as a feature anywhere in this project.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vader = SentimentIntensityAnalyzer()


def compute_vader_scores(texts: Sequence[str]) -> pd.DataFrame:
    """Score each text with VADER's rule-based sentiment lexicon.

    Args:
        texts: Raw post text.

    Returns:
        DataFrame with columns `vader_neg`, `vader_neu`, `vader_pos`,
        `vader_compound`, one row per input text, in input order.
    """
    rows = [_vader.polarity_scores(str(t)) for t in texts]
    return pd.DataFrame(rows).rename(columns=lambda c: f"vader_{c}")


def compute_textblob_scores(texts: Sequence[str]) -> pd.DataFrame:
    """Score each text with TextBlob's pattern-based sentiment analyser.

    Args:
        texts: Raw post text.

    Returns:
        DataFrame with columns `textblob_polarity` (-1 negative to +1
        positive) and `textblob_subjectivity` (0 objective to 1 subjective).
    """
    rows = [
        {"textblob_polarity": tb.sentiment.polarity, "textblob_subjectivity": tb.sentiment.subjectivity}
        for tb in (TextBlob(str(t)) for t in texts)
    ]
    return pd.DataFrame(rows)
