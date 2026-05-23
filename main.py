"""mini-lang: typecheck and run expressions.

    uv run python main.py                 start a REPL
    uv run python main.py 'EXPR'          typecheck and run one expression
    uv run python main.py --demo          tour of accepted and rejected programs
"""
import os
import sys
from lexer import lex
from parser import Parser
from evaluator import eval, Closure
from context import show_type
from errors import TypeCheckError
from type_checker import typecheck_expr
from examples import ACCEPT, REJECT

_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _style(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def green(s):
    return _style("32", s)


def red(s):
    return _style("31", s)


def dim(s):
    return _style("2", s)


def bold(s):
    return _style("1", s)


def show_value(v) -> str:
    return "<function>" if isinstance(v, Closure) else str(v)


def run(src: str) -> tuple[str, str]:
    """Typecheck and evaluate `src`, returning (type, value) as strings."""
    expr = Parser(lex(src))()
    t = typecheck_expr(expr)
    return show_type(t), show_value(eval(expr, {}))


def report(src: str) -> bool:
    """Print the result of running `src`. Returns whether it typechecked."""
    try:
        t, v = run(src)
    except SyntaxError as err:
        print(red(f"  syntax error: {err}"))
        return False
    except TypeCheckError as err:
        head, *trace = str(err).split("\n")
        print(red(f"  type error {head}"))
        for line in trace:
            print(dim(f"  {line}"))
        return False
    print(f"  : {green(t)}")
    print(f"  = {v}")
    return True


def demo():
    print(bold("Accepted\n"))
    for ex in ACCEPT:
        print(dim(f"-- {ex.title}"))
        print(f"> {ex.src}")
        report(ex.src)
        print()
    print(bold("Rejected\n"))
    for ex in REJECT:
        print(dim(f"-- {ex.title}"))
        print(f"> {ex.src}")
        report(ex.src)
        print()


def repl():
    print("mini-lang. Enter an expression, or :q to quit.")
    while True:
        try:
            src = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if src in (":q", ":quit"):
            return
        if src:
            report(src)


def main(argv: list[str]) -> int:
    match argv:
        case []:
            repl()
        case ["--demo"]:
            demo()
        case ["-h" | "--help"]:
            print(__doc__)
        case [src]:
            print(f"> {src}")
            return 0 if report(src) else 1
        case _:
            print(__doc__)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
