# Running whole programs: declarations, definitions and a final
# expression, checked and evaluated in order. Shared by files and the REPL.
from dataclasses import dataclass, field
from lexer import lex
from parser import Parser, Program, DeclGroup, Definition, Expr, Type
from context import TypeTable, show_type
from evaluator import eval, bind, ConValue, Value, show_value
from types_table import declare_group
from type_checker import typecheck_expr, typecheck_definition


@dataclass(frozen=True)
class Declared:
    names: tuple[str, ...]


@dataclass(frozen=True)
class Defined:
    name: str
    type: Type
    value: Value


@dataclass(frozen=True)
class Result:
    type: Type
    value: Value


Output = Declared | Defined | Result


@dataclass
class Session:
    """Everything declared and defined so far."""

    table: TypeTable = field(default_factory=TypeTable)
    types: dict[str, Type] = field(default_factory=dict)
    values: dict[str, Value] = field(default_factory=dict)

    def declare(self, group: DeclGroup) -> Declared:
        self.table = declare_group(self.table, group)
        for decl in group.decls:
            for con, fields in decl.constructors:
                self.values[con] = ConValue(con, len(fields))
        return Declared(tuple(d.name for d in group.decls))

    def define(self, d: Definition) -> Defined:
        t = typecheck_definition(d, self.types, self.table)
        # bind copies the environment, so closures see the definitions made
        # so far and not later redefinitions.
        self.values = bind(self.values, d.name, d.value, d.rec)
        self.types[d.name] = t
        return Defined(d.name, t, self.values[d.name])

    def typecheck(self, expr: Expr) -> Type:
        return typecheck_expr(expr, self.types, self.table)

    def evaluate(self, expr: Expr) -> Result:
        t = self.typecheck(expr)
        return Result(t, eval(expr, self.values))

    def run_program(self, program: Program) -> list[Output]:
        """Run each item in order. An error stops the program, but items
        before it stay declared and defined."""
        outputs: list[Output] = []
        for item in program.items:
            match item:
                case DeclGroup():
                    outputs.append(self.declare(item))
                case Definition():
                    outputs.append(self.define(item))
        if program.expr is not None:
            outputs.append(self.evaluate(program.expr))
        return outputs

    def run_source(self, src: str) -> list[Output]:
        return self.run_program(Parser(lex(src)).parse_program())


def final_result(outputs: list[Output]) -> Result | None:
    """A program's answer: its final expression, or else `main`."""
    for out in reversed(outputs):
        if isinstance(out, Result):
            return out
    for out in reversed(outputs):
        if isinstance(out, Defined) and out.name == "main":
            return Result(out.type, out.value)
    return None


def run(src: str, session: Session | None = None) -> tuple[str, str]:
    """Typecheck and evaluate a program, returning its answer's (type,
    value) as strings."""
    result = final_result((session or Session()).run_source(src))
    if result is None:
        raise ValueError("program has no final expression or main")
    return show_type(result.type), show_value(result.value)
