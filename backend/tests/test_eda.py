import pytest

from app.processing.eda import summarize


def test_summary_known_values():
    assert summarize([1,2,3,4])==dict(count=4,minimum=1,median=2.5,maximum=4,mean=2.5,zero_count=0,distinct_count=4)
    assert summarize([False,True])["mean"]==0.5
    with pytest.raises(ValueError):
        summarize([])
