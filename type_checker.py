from lexer import lex
from parser import (
    Parser,
    Expr,
    Var,
    Lam,
    App,
    IntLit,
    Add,
    Anno,
    Type,
    IntType,
    FunType,
)

Context = dict[str, Type]
StaticInt = IntType()


def synth(expr: Expr, ctx: Context) -> Type:
    match expr:
        case Var(name):
            if name not in ctx:
                raise TypeError(f"Unbound Variable: {name}")
            return ctx[name]
        case IntLit(_):
            return StaticInt
        case Add(lhs, rhs):
            check(lhs, ctx, StaticInt)
            check(rhs, ctx, StaticInt)
            return StaticInt
        case App(fn, arg):
            function_type = synth(fn, ctx)
            if not isinstance(function_type, FunType):
                raise TypeError(f"Trying to apply {fn} which isn't a function")
            check(arg, ctx, function_type.param)
            return function_type.result
        case Anno(inner, annotated_type):
            check(inner, ctx, annotated_type)
            return annotated_type
        case Lam(_, _):
            raise TypeError(
                f"Cannot synthesize type of lambda {expr}; Lambdas require context to typecheck"
            )

        case _:
            raise TypeError(
                f"Tried to synthesize the type of {expr}, which is not valid"
            )


def check(expr: Expr, ctx: Context, expected_type: Type):
    if isinstance(expr, Lam):
        if not isinstance(expected_type, FunType):
            raise TypeError(
                f"Lambda {expr} checked against non-function type {expected_type}"
            )
        new_context = {**ctx, expr.param: expected_type.param}
        check(expr.body, new_context, expected_type.result)
        return
    final_attempt = synth(expr, ctx)
    if final_attempt != expected_type:
        raise TypeError(
            f"Expected {expected_type} after synthing {expr} but got {final_attempt}"
        )


def typecheck(src: str) -> Type:
    return synth(Parser(lex(src))(), {})
