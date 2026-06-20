from parser import Lam, Var, Con, App, Expr, Add, IntLit, Anno, Let
from dataclasses import dataclass


@dataclass
class Closure:
    param: str
    body: Expr
    env: dict[str, "Value"]


# A constructor applied to some of its arguments. It's a finished value
# once len(args) == arity; until then applying it collects one more.
@dataclass(frozen=True)
class ConValue:
    name: str
    arity: int
    args: tuple["Value", ...] = ()


Value = Closure | ConValue | int | str


def show_value(v: Value) -> str:
    """Print a value the way it would be written in source."""
    if _is_function(v):
        return "<function>"
    if isinstance(v, ConValue):
        parts = [v.name]
        for arg in v.args:
            s = show_value(arg)
            if isinstance(arg, ConValue) and arg.args and not _is_function(arg):
                s = f"({s})"
            parts.append(s)
        return " ".join(parts)
    return str(v)


def _is_function(v: Value) -> bool:
    return isinstance(v, Closure) or (
        isinstance(v, ConValue) and len(v.args) < v.arity
    )


def eval(e: Expr, env: dict[str, "Value"]):
    match e:
        case Var(name) | Con(name):
            # Constructors are put in the environment when their type is
            # declared, as ConValues with no arguments yet.
            return env[name]
        case Lam(param, body):
            return Closure(param, body, env)
        case App(func, arg):
            closure = eval(func, env)
            if isinstance(closure, ConValue) and len(closure.args) < closure.arity:
                return ConValue(
                    closure.name, closure.arity, closure.args + (eval(arg, env),)
                )
            if not isinstance(closure, Closure):
                raise TypeError(f"Can't call nonfunction {closure}")
            new_env = {**closure.env, closure.param: eval(arg, env)}
            return eval(closure.body, new_env)
        case Add(lhs, rhs):
            l = eval(lhs, env)
            r = eval(rhs, env)
            if not isinstance(l, int) or not isinstance(r, int):
                raise TypeError(f"Cannot add non-integers: {l} + {r}")
            return l + r
        case IntLit(v):
            return v
        case Anno(inner, _):
            return eval(inner, env)
        case Let(name, _, value, body):
            return eval(body, {**env, name: eval(value, env)})
        case _:
            raise TypeError(f"Unknown ast node {e}")
