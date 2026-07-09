"""mini-lang: typecheck and run programs.

    uv run python main.py                 start a REPL
    uv run python main.py 'EXPR'          typecheck and run one expression
    uv run python main.py FILE            typecheck and run a program file
    uv run python main.py --demo          tour of accepted and rejected programs
"""
import os
import sys
from lexer import lex
from parser import Parser
from context import show_type
from evaluator import show_value
from errors import TypeCheckError
from program import Session, Declared, Defined, Result, Warning, final_result
from examples import ACCEPT, REJECT

REPL_HELP = """\
  EXPR                     typecheck and evaluate, printing value : type
  let x = EXPR             define x for the rest of the session
  let x : TYPE = EXPR      define x with an annotated (maybe polymorphic) type
  type T a = K1 | K2 a     declare a data type
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


def yellow(s):
    return _style("33", s)


def dim(s):
    return _style("2", s)


def bold(s):
    return _style("1", s)


def _print_error(err: Exception):
    if isinstance(err, TypeCheckError):
        head, *trace = str(err).split("\n")
        print(red(f"  type error {head}"))
        for line in trace:
            print(dim(f"  {line}"))
    elif isinstance(err, SyntaxError):
        print(red(f"  syntax error: {err}"))
    else:
        print(red(f"  runtime error: {err}"))


_ERRORS = (SyntaxError, TypeCheckError, RuntimeError)


def _print_result(result: Result):
    print(f"  {show_value(result.value)} : {green(show_type(result.type))}")


def report(src: str, session: Session | None = None) -> bool:
    """Run a program and print its answer as `value : type`. Returns
    whether it ran."""
    try:
        outputs = (session or Session()).run_source(src)
    except _ERRORS as err:
        _print_error(err)
        return False
    for out in outputs:
        if isinstance(out, Warning):
            print(yellow(f"  warning: {out.message}"))
    result = final_result(outputs)
    if result is not None:
        _print_result(result)
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
            for out in session.run_source(line):
                match out:
                    case Declared(names):
                        print(dim(f"  declared {', '.join(names)}"))
                    case Defined(name, t, v):
                        print(f"  {name} = {show_value(v)} : {green(show_type(t))}")
                    case Result():
                        _print_result(out)
                    case Warning(message):
                        print(yellow(f"  warning: {message}"))
    except _ERRORS as err:
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
