# Running whole programs: declarations, definitions and a final
# expression, checked and evaluated in order. Shared by files and the REPL.
from dataclasses import dataclass, field
from lexer import lex
from parser import Parser, Program, DeclGroup, Definition, Expr, Type
from context import TypeTable, show_type
from evaluator import eval, bind, ConValue, Value, show_value
from types_table import declare_group, builtin_table
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


@dataclass(frozen=True)
class Warning:
    message: str


Output = Declared | Defined | Result | Warning


@dataclass
class Session:
    """Everything declared and defined so far."""

    table: TypeTable = field(default_factory=builtin_table)
    types: dict[str, Type] = field(default_factory=dict)
    values: dict[str, Value] = field(default_factory=dict)

    def __post_init__(self):
        # Constructors of the built-in types (the tuples) need values too.
        for name, info in self.table.ctors.items():
            self.values.setdefault(name, ConValue(name, len(info.fields)))

    def declare(self, group: DeclGroup) -> Declared:
        self.table = declare_group(self.table, group)
        for decl in group.decls:
            for con, fields in decl.constructors:
                self.values[con] = ConValue(con, len(fields))
        return Declared(tuple(d.name for d in group.decls))

    def define(self, d: Definition, warnings: list[str] | None = None) -> Defined:
        t = typecheck_definition(d, self.types, self.table, warnings)
        # bind copies the environment, so closures see the definitions made
        # so far and not later redefinitions.
        self.values = bind(self.values, d.name, d.value, d.rec)
        self.types[d.name] = t
        return Defined(d.name, t, self.values[d.name])

    def typecheck(self, expr: Expr) -> Type:
        return typecheck_expr(expr, self.types, self.table)

    def evaluate(self, expr: Expr, warnings: list[str] | None = None) -> Result:
        t = typecheck_expr(expr, self.types, self.table, warnings)
        return Result(t, eval(expr, self.values))

    def run_program(self, program: Program) -> list[Output]:
        """Run each item in order. An error stops the program, but items
        before it stay declared and defined."""
        outputs: list[Output] = []
        for item in program.items:
            warnings: list[str] = []
            match item:
                case DeclGroup():
                    out = self.declare(item)
                case Definition():
                    out = self.define(item, warnings)
            outputs += [Warning(w) for w in warnings] + [out]
        if program.expr is not None:
            warnings = []
            out = self.evaluate(program.expr, warnings)
            outputs += [Warning(w) for w in warnings] + [out]
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
