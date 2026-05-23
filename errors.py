from contextlib import contextmanager


class TypeCheckError(TypeError):
    """A type error tagged with the Dunfield & Krishnaswami (2013) rule that
    failed, plus the chain of rules the checker was inside when it did."""

    def __init__(self, rule: str, message: str):
        super().__init__(message)
        self.rule = rule
        self.message = message
        # (rule, description) pairs, innermost first
        self.trace: list[tuple[str, str]] = []

    def __str__(self) -> str:
        lines = [f"[{self.rule}] {self.message}"]
        lines += [f"  while {what}  ({rule})" for rule, what in self.trace]
        return "\n".join(lines)


@contextmanager
def rule_frame(rule: str, description: str):
    """Record that a failure inside this block happened while applying `rule`."""
    try:
        yield
    except TypeCheckError as err:
        err.trace.append((rule, description))
        raise
