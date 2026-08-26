class Calculator:
    def add(self, left: int, right: int) -> int:
        return left + right

    def subtract(self, left: int, right: int) -> int:
        return left - right

    def multiply(self, left: int, right: int) -> int:
        return left * right


def run_tests() -> None:
    assert Calculator().add(2, 3) == 5
    assert Calculator().subtract(5, 3) == 2
    assert Calculator().multiply(4, 3) == 12


if __name__ == "__main__":
    run_tests()
