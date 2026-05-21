# Bidirectional typing (Dunfield & Krishnaswami 2013, Fig. 11).
#
#   check:      Γ ⊢ e ⇐ A ⊣ Δ
#   synth:      Γ ⊢ e ⇒ A ⊣ Δ
#   app_synth:  Γ ⊢ A • e ⇒⇒ C ⊣ Δ   (applying a function of type A to e)
#
# Each takes the input context Γ and returns the output context Δ.
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
    TVar,
    Forall,
    Exists,
)
from context import Context, CVar, CTVar, CExists, substitute, show_type, fresh
from subtyping import subtype

StaticInt = IntType()


def _rename_tvar(expr: Expr, name: str, new_name: str) -> Expr:
    """Rename type variable `name` in every annotation inside `expr`."""
    match expr:
        case Anno(inner, t):
            return Anno(
                _rename_tvar(inner, name, new_name),
                substitute(t, name, TVar(new_name)),
            )
        case Lam(param, body):
            return Lam(param, _rename_tvar(body, name, new_name))
        case App(fn, arg):
            return App(
                _rename_tvar(fn, name, new_name), _rename_tvar(arg, name, new_name)
            )
        case Add(lhs, rhs):
            return Add(
                _rename_tvar(lhs, name, new_name), _rename_tvar(rhs, name, new_name)
            )
        case Var(_) | IntLit(_):
            return expr


def synth(ctx: Context, expr: Expr) -> tuple[Type, Context]:
    """Γ ⊢ e ⇒ A ⊣ Δ"""
    match expr:
        case Var(name):
            # Var
            found = ctx.lookup(name)
            if found is None:
                raise TypeError(f"Unbound Variable: {name}")
            return found, ctx
        case IntLit(_):
            # 1I⇒
            return StaticInt, ctx
        case Add(lhs, rhs):
            ctx = check(ctx, lhs, StaticInt)
            ctx = check(ctx, rhs, StaticInt)
            return StaticInt, ctx
        case Anno(inner, annotated_type):
            # Anno
            if not ctx.well_formed(annotated_type):
                raise TypeError(
                    f"Annotation {show_type(annotated_type)} is not well-formed in [{ctx}]"
                )
            return annotated_type, check(ctx, inner, annotated_type)
        case Lam(param, body):
            # →I⇒: guess α̂ → β̂ and check the body. α̂ and β̂ stay in Δ so
            # the caller can see what they were solved to; there's no
            # let-generalization.
            a, b = Exists(fresh("a")), Exists(fresh("b"))
            ctx = ctx.extend(CExists(a.name), CExists(b.name), CVar(param, a))
            delta = check(ctx, body, b).drop(CVar(param, a))
            return FunType(a, b), delta
        case App(fn, arg):
            # →E
            fn_type, theta = synth(ctx, fn)
            return app_synth(theta, theta.apply(fn_type), arg)
    raise TypeError(f"Tried to synthesize the type of {expr}, which is not valid")


def check(ctx: Context, expr: Expr, expected_type: Type) -> Context:
    """Γ ⊢ e ⇐ A ⊣ Δ"""
    match expr, expected_type:
        case IntLit(_), IntType():
            # 1I
            return ctx
        case _, Forall(var, body):
            # ∀I. Annotations inside e may mention var, so it keeps its name
            # unless that would shadow a type variable already in scope.
            if ctx.has_tvar(var):
                renamed = fresh(var)
                expr = _rename_tvar(expr, var, renamed)
                body = substitute(body, var, TVar(renamed))
                var = renamed
            return check(ctx.extend(CTVar(var)), expr, body).drop(CTVar(var))
        case Lam(param, body), FunType(param_type, result_type):
            # →I
            ctx = ctx.extend(CVar(param, param_type))
            return check(ctx, body, result_type).drop(CVar(param, param_type))
    # Sub
    synthed, theta = synth(ctx, expr)
    return subtype(theta, theta.apply(synthed), theta.apply(expected_type))


def app_synth(ctx: Context, fn_type: Type, arg: Expr) -> tuple[Type, Context]:
    """Γ ⊢ A • e ⇒⇒ C ⊣ Δ"""
    match fn_type:
        case Forall(var, body):
            # ∀App: instantiate the forall with a fresh existential
            a = fresh(var)
            ctx = ctx.extend(CExists(a))
            return app_synth(ctx, substitute(body, var, Exists(a)), arg)
        case Exists(name) if CExists(name) in ctx.entries:
            # α̂App: α̂ must be a function, so split it into α̂₁ → α̂₂
            ctx, a1, a2 = ctx.split_arrow(name)
            return a2, check(ctx, arg, a1)
        case FunType(param, result):
            # →App
            return result, check(ctx, arg, param)
    raise TypeError(f"Trying to apply a value of type {show_type(fn_type)}")


def typecheck(src: str) -> Type:
    t, ctx = synth(Context(), Parser(lex(src))())
    return ctx.apply(t)
