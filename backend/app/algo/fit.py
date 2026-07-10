def least_squares(x, y) -> tuple[float, float]:
    """
    一元线性最小二乘拟合 y = k*x + b
    :param x: 自变量序列，list/tuple
    :param y: 因变量序列，list/tuple
    :return: k(斜率), b(截距)
    """
    # 校验数据长度一致
    if len(x) != len(y):
        raise ValueError("x 和 y 的长度必须相等")
    n = len(x)
    if n < 2:
        raise ValueError("至少需要2组数据进行拟合")

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y, strict=True))
    sum_x2 = sum(xi**2 for xi in x)

    denominator = n * sum_x2 - sum_x**2
    if denominator == 0:
        raise ZeroDivisionError("分母为0，所有x值相同，无法拟合直线")

    k = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - k * sum_x) / n

    return k, b
