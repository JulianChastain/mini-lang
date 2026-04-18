from parser import Lam, Var, App
from ast import Expr
from dataclasses import dataclass


@dataclass
class Closure:
    param: str
    body: Expr
    env: dict[str, "Value"]


Value = Closure | str


def eval(e: Expr, env: dict[str, "Value"]):
    match e:
        case Var(name):
            return env[name]
        case Lam(param, body):
            return Closure(param, body, env)
        case App(func, arg):
            closure = eval(func, env)
            if not isinstance(closure, Closure):
                raise TypeError(f"Can't call nonfunction {closure}")
            new_env = {**closure.env, closure.param: eval(arg, env)}
            return eval(closure.body, new_env)
        case _:
            raise TypeError(f"Unknown ast node {e}")
