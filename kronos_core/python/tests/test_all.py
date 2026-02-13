import pytest
import kronos_core


def test_sum_as_string():
    assert kronos_core.sum_as_string(1, 1) == "2"
