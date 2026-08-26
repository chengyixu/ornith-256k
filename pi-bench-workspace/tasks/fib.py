def fib(n):
    """Return the nth Fibonacci number (fib(0)=0, fib(1)=1) using iteration."""
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


if __name__ == "__main__":
    assert fib(10) == 55, "fib(10) should be 55"
    print(f"fib(10) = {fib(10)}")
    print("fib(10) == 55 passed")

    for bad in (-1, -5):
        try:
            fib(bad)
        except ValueError as e:
            print(f"fib({bad}) correctly raised ValueError: {e}")
        else:
            raise AssertionError(f"fib({bad}) should have raised ValueError")
