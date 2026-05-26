"""mini-lang: typecheck and run expressions.

    uv run python main.py                 start a REPL
    uv run python main.py 'EXPR'          typecheck and run one expression
    uv run python main.py FILE            typecheck and run a program file
    uv run python main.py --demo          tour of accepted and rejected programs
"""
import os
import sys
from dataclasses import dataclass, field
from lexer import lex
from parser import Parser, Expr, Definition, Anno, Type
from evaluator import eval, Closure
from context import show_type
from errors import TypeCheckError
from type_checker import typecheck_expr
from examples import ACCEPT, REJECT

REPL_HELP = """\
  EXPR                     typecheck and evaluate, printing value : type
  let x = EXPR             define x for the rest of the session
  let x : TYPE = EXPR      define x with an annotated (maybe polymorphic) type
  :t EXPR                  print the type without evaluating
  :env                     list definitions
  :q                       quit"""

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


@dataclass
class Session:
    """Names defined so far, with their closed types and values."""

    types: dict[str, Type] = field(default_factory=dict)
    values: dict[str, object] = field(default_factory=dict)

    def typecheck(self, expr: Expr) -> Type:
        return typecheck_expr(expr, self.types)

    def run(self, expr: Expr) -> tuple[Type, object]:
        t = self.typecheck(expr)
        return t, eval(expr, self.values)

    def define(self, d: Definition) -> tuple[Type, object]:
        # A top-level definition is checked like a whole program, so
        # leftover existentials are generalized, as for any program. Only
        # lets inside an expression stay monomorphic.
        value = d.value if d.type is None else Anno(d.value, d.type)
        t, v = self.run(value)
        self.types[d.name] = t
        self.values[d.name] = v
        return t, v


def run(src: str, session: Session | None = None) -> tuple[str, str]:
    """Typecheck and evaluate `src`, returning (type, value) as strings."""
    t, v = (session or Session()).run(Parser(lex(src))())
    return show_type(t), show_value(v)


def _print_error(err: Exception):
    if isinstance(err, TypeCheckError):
        head, *trace = str(err).split("\n")
        print(red(f"  type error {head}"))
        for line in trace:
            print(dim(f"  {line}"))
    else:
        print(red(f"  syntax error: {err}"))


def report(src: str, session: Session | None = None) -> bool:
    """Print `value : type` for `src`. Returns whether it typechecked."""
    try:
        t, v = run(src, session)
    except (SyntaxError, TypeCheckError) as err:
        _print_error(err)
        return False
    print(f"  {v} : {green(t)}")
    return True


def demo():
    for heading, examples in (("Accepted", ACCEPT), ("Rejected", REJECT)):
        print(bold(f"{heading}\n"))
        for ex in examples:
            print(dim(f"-- {ex.title}"))
            print(f"> {ex.src}")
            report(ex.src)
            print()


def repl_line(session: Session, line: str):
    """Handle one line of REPL input."""
    try:
        if line == ":env":
            for name, t in session.types.items():
                print(f"  {name} : {green(show_type(t))}")
        elif line.startswith(":t "):
            t = session.typecheck(Parser(lex(line[3:]))())
            print(f"  {green(show_type(t))}")
        else:
            parsed = Parser(lex(line)).parse_repl_input()
            if isinstance(parsed, Definition):
                t, v = session.define(parsed)
                print(f"  {parsed.name} = {show_value(v)} : {green(show_type(t))}")
            else:
                t, v = session.run(parsed)
                print(f"  {show_value(v)} : {green(show_type(t))}")
    except (SyntaxError, TypeCheckError) as err:
        _print_error(err)


def repl():
    print("mini-lang. :help for commands, :q to quit.")
    session = Session()
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if line in (":q", ":quit"):
            return
        if line in (":h", ":help"):
            print(REPL_HELP)
        elif line:
            repl_line(session, line)


def main(argv: list[str]) -> int:
    match argv:
        case []:
            repl()
        case ["--demo"]:
            demo()
        case ["-h" | "--help"]:
            print(__doc__)
        case [path] if os.path.isfile(path):
            with open(path) as f:
                return 0 if report(f.read()) else 1
        case [src]:
            print(f"> {src}")
            return 0 if report(src) else 1
        case _:
            print(__doc__)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
