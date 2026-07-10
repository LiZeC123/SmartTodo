import pytest

from app.algo.fit import least_squares


def test_fit_least_squares():
    x = [1]
    y = [2]

    with pytest.raises(ValueError):
        least_squares(x, y)

    x.append(2)
    with pytest.raises(ValueError):
        least_squares(x, y)

    y.append(3)
    k, b = least_squares(x, y)
    assert k == 1
    assert b == 1

    x = [1, 1]
    y = [2, 3]
    with pytest.raises(ZeroDivisionError):
        least_squares(x, y)
