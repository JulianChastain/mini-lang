from parser import (
    Lam,
    Var,
    Con,
    App,
    Expr,
    BinOp,
    IntLit,
    Anno,
    Let,
    Match,
    Pattern,
    PVar,
    PWild,
    PInt,
    PCon,
)
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


class MatchError(RuntimeError):
    """No branch of a match fit the value."""


def match_pattern(p: Pattern, v: Value, bindings: dict[str, Value]) -> bool:
    """Whether `v` fits `p`, adding the pattern's variables to `bindings`."""
    match p:
        case PVar(name):
            bindings[name] = v
            return True
        case PWild():
            return True
        case PInt(n):
            return v == n
        case PCon(name, args):
            return (
                isinstance(v, ConValue)
                and v.name == name
                and len(v.args) == len(args)
                and all(match_pattern(q, w, bindings) for q, w in zip(args, v.args))
            )


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


def bind(env: dict[str, Value], name: str, value: Expr, rec: bool) -> dict[str, Value]:
    """A copy of `env` with `name` bound to `value`'s result.

    For `let rec`, closures made while evaluating `value` capture the new
    environment, which gets `name` added afterwards, so they can call it.
    """
    new_env = dict(env)
    new_env[name] = eval(value, new_env if rec else env)
    return new_env


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
        case BinOp(op, lhs, rhs):
            l = eval(lhs, env)
            r = eval(rhs, env)
            if not isinstance(l, int) or not isinstance(r, int):
                raise TypeError(f"Cannot apply {op} to non-integers: {l} {op} {r}")
            match op:
                case "+":
                    return l + r
                case "-":
                    return l - r
                case "*":
                    return l * r
                case "==":
                    return ConValue("True" if l == r else "False", 0)
                case "<":
                    return ConValue("True" if l < r else "False", 0)
        case IntLit(v):
            return v
        case Anno(inner, _):
            return eval(inner, env)
        case Match(scrutinee, branches):
            # The first branch that fits wins.
            v = eval(scrutinee, env)
            for pattern, body in branches:
                bindings: dict[str, Value] = {}
                if match_pattern(pattern, v, bindings):
                    return eval(body, {**env, **bindings})
            raise MatchError(f"no branch matches {show_value(v)}")
        case Let(name, _, value, body, rec):
            return eval(body, bind(env, name, value, rec))
        case _:
            raise TypeError(f"Unknown ast node {e}")
