def total(values: list[int]) -> int:
    return sum(values)


if total([1, 2, 3]) != 6:
    raise AssertionError("total must sum all values")
