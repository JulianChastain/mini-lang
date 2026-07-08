# Bidirectional typing (Dunfield & Krishnaswami 2013, Fig. 11).
#
#   check:      Γ ⊢ e ⇐ A ⊣ Δ
#   synth:      Γ ⊢ e ⇒ A ⊣ Δ
#   app_synth:  Γ ⊢ A • e ⇒⇒ C ⊣ Δ   (applying a function of type A to e)
#
# Each takes the input context Γ and returns the output context Δ.
from itertools import count
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
    Let,
    Type,
    IntType,
    FunType,
    TVar,
    Forall,
    Exists,
    TCon,
    Con,
    Definition,
    DeclGroup,
    Program,
    Match,
)
from context import (
    Context,
    CVar,
    CTVar,
    CExists,
    CMarker,
    substitute,
    show_type,
    fresh,
    reset_fresh,
    TypeTable,
)
from types_table import declare_group
from patterns import check_pattern, show_pattern, pattern_vars, instantiate
from exhaustiveness import missing_case
from errors import TypeCheckError, rule_frame
from subtyping import subtype

StaticInt = IntType()


def show_expr(expr: Expr, prec: int = 0) -> str:
    """Print an expression in surface syntax with minimal parentheses.

    Precedence, loosest first: lambda and let (0), `+` (1), application (2),
    atom (3).
    """
    match expr:
        case Var(name) | Con(name):
            return name
        case IntLit(value):
            return str(value)
        case Anno(inner, t):
            # A bare lambda would parse here too, but reads ambiguously.
            return f"({show_expr(inner, 1)} : {show_type(t)})"
        case Lam(param, body):
            s, own = f"/{param} -> {show_expr(body)}", 0
        case Let(name, t, value, body, rec):
            keyword = "let rec" if rec else "let"
            annotation = "" if t is None else f" : {show_type(t)}"
            s = f"{keyword} {name}{annotation} = {show_expr(value)} in {show_expr(body)}"
            own = 0
        case Match(scrutinee, branches):
            parts = [f"match {show_expr(scrutinee)} with"]
            for i, (pattern, body) in enumerate(branches):
                b = show_expr(body)
                if i < len(branches) - 1 and _ends_with_match(body):
                    b = f"({b})"
                parts.append(f"| {show_pattern(pattern)} -> {b}")
            s, own = " ".join(parts), 0
        case Add(lhs, rhs):
            s, own = f"{show_expr(lhs, 1)} + {show_expr(rhs, 2)}", 1
        case App(fn, arg):
            s, own = f"{show_expr(fn, 2)} {show_expr(arg, 3)}", 2
    return f"({s})" if prec > own else s


def _ends_with_match(expr: Expr) -> bool:
    """Whether a match would swallow branches printed after `expr`."""
    match expr:
        case Match():
            return True
        case Lam(_, body) | Let(_, _, _, body):
            return _ends_with_match(body)
    return False


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
        case Let(x, t, value, body, rec):
            return Let(
                x,
                None if t is None else substitute(t, name, TVar(new_name)),
                _rename_tvar(value, name, new_name),
                _rename_tvar(body, name, new_name),
                rec,
            )
        case Match(scrutinee, branches):
            return Match(
                _rename_tvar(scrutinee, name, new_name),
                tuple((p, _rename_tvar(b, name, new_name)) for p, b in branches),
            )
        case Var(_) | Con(_) | IntLit(_):
            return expr


def _let_binding(
    ctx: Context, name: str, annotation: Type | None, value: Expr, rec: bool = False
) -> tuple[Type, Context]:
    """The type x gets in `let x [: A] = e1 in e2`, and the context after e1.

    With an annotation, e1 is checked against A, so x can be polymorphic.
    Without one, x gets e1's synthesized type as is: the paper doesn't
    generalize, so an unannotated x is monomorphic (its existentials are
    shared by every use).

    `let rec` requires the annotation and checks e1 with x : A already in
    scope: Γ, x : A ⊢ e1 ⇐ A ⊣ Θ, x : A, Θ'.
    """
    if rec:
        if annotation is None:
            raise TypeCheckError("LetRec", f"let rec {name} needs a type annotation")
        if reason := ctx.why_ill_formed(annotation):
            raise TypeCheckError(
                "LetRec", f"bad annotation {show_type(annotation)} on {name}: {reason}"
            )
        with rule_frame("LetRec", f"checking {name} against {show_type(annotation)}"):
            inner = ctx.extend(CVar(name, annotation))
            return annotation, check(inner, value, annotation).drop(CVar(name, annotation))
    if annotation is None:
        with rule_frame("Let", f"inferring the type of {name}"):
            t, theta = synth(ctx, value)
        return theta.apply(t), theta
    if reason := ctx.why_ill_formed(annotation):
        raise TypeCheckError(
            "Let", f"bad annotation {show_type(annotation)} on {name}: {reason}"
        )
    with rule_frame("Let", f"checking {name} against {show_type(annotation)}"):
        return annotation, check(ctx, value, annotation)


def synth(ctx: Context, expr: Expr) -> tuple[Type, Context]:
    """Γ ⊢ e ⇒ A ⊣ Δ"""
    match expr:
        case Var(name):
            # Var
            found = ctx.lookup(name)
            if found is None:
                raise TypeCheckError("Var", f"unbound variable {name}")
            return found, ctx
        case Con(name):
            # Con: a constructor is a polymorphic function from its fields
            # to its type, so ∀App and →App handle applying it.
            info = ctx.table.ctors.get(name)
            if info is None:
                raise TypeCheckError("Con", f"unknown constructor {name}")
            return info.scheme, ctx
        case IntLit(_):
            # 1I⇒
            return StaticInt, ctx
        case Add(lhs, rhs):
            ctx = check(ctx, lhs, StaticInt)
            ctx = check(ctx, rhs, StaticInt)
            return StaticInt, ctx
        case Anno(inner, annotated_type):
            # Anno
            if reason := ctx.why_ill_formed(annotated_type):
                raise TypeCheckError(
                    "Anno", f"bad annotation {show_type(annotated_type)}: {reason}"
                )
            return annotated_type, check(ctx, inner, annotated_type)
        case Lam(param, body):
            # →I⇒: guess α̂ → β̂ and check the body. α̂ and β̂ stay in Δ so
            # the caller can see what they were solved to; typecheck()
            # generalizes whatever is still unsolved at the very end.
            a, b = Exists(fresh("a")), Exists(fresh("b"))
            with rule_frame("→I⇒", f"inferring the type of {show_expr(expr)}"):
                ctx = ctx.extend(CExists(a.name), CExists(b.name), CVar(param, a))
                delta = check(ctx, body, b).drop(CVar(param, a))
            return FunType(a, b), delta
        case App(fn, arg):
            # →E
            fn_type, theta = synth(ctx, fn)
            return app_synth(theta, theta.apply(fn_type), arg)
        case Let(name, annotation, value, body, rec):
            # Let⇒. Unlike →I, only the x : A entry is removed afterwards:
            # existentials the body introduced after it may appear in the
            # result type, and types never mention term variables.
            t, theta = _let_binding(ctx, name, annotation, value, rec)
            result, delta = synth(theta.extend(CVar(name, t)), body)
            return result, delta.replace(CVar(name, t))
        case Match():
            # Match⇒: like →I⇒, guess β̂ for the result and check against it.
            b = fresh("b")
            ctx = ctx.extend(CExists(b))
            return Exists(b), _check_match(ctx, expr, Exists(b))
    raise TypeCheckError("Sub", f"cannot synthesize a type for {expr}")


def check(ctx: Context, expr: Expr, expected_type: Type) -> Context:
    """Γ ⊢ e ⇐ A ⊣ Δ"""
    judgment = f"checking {show_expr(expr)} against {show_type(ctx.apply(expected_type))}"
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
            with rule_frame("∀I", judgment):
                return check(ctx.extend(CTVar(var)), expr, body).drop(CTVar(var))
        case Lam(param, body), FunType(param_type, result_type):
            # →I
            with rule_frame("→I", judgment):
                ctx = ctx.extend(CVar(param, param_type))
                return check(ctx, body, result_type).drop(CVar(param, param_type))
        case Match(), _:
            with rule_frame("Match", judgment):
                return _check_match(ctx, expr, expected_type)
        case Let(name, annotation, value, body, rec), _:
            # Let⇐: like →I, the body is checked so a lambda in it still
            # gets the expected type pushed in.
            t, theta = _let_binding(ctx, name, annotation, value, rec)
            return check(theta.extend(CVar(name, t)), body, expected_type).drop(
                CVar(name, t)
            )
    # Sub
    with rule_frame("Sub", judgment):
        synthed, theta = synth(ctx, expr)
        return subtype(theta, theta.apply(synthed), theta.apply(expected_type))


def _check_match(ctx: Context, expr: Match, expected_type: Type) -> Context:
    """Match⇐: Γ ⊢ match e with | p -> e' ... ⇐ C ⊣ Δ

    The scrutinee's type is synthesized (and instantiated, if it's
    polymorphic). Each branch then runs between a marker and a drop back to
    it: Γ, ▶ ⊢ p ⇐ A ⊣ Θ, then Θ ⊢ e' ⇐ [Θ]C ⊣ Δ, ▶, Δ'. Dropping removes
    the branch's variables and any existentials its patterns introduced.
    """
    t, ctx = synth(ctx, expr.scrutinee)
    ctx, t = instantiate(ctx, ctx.apply(t))
    ctx = ctx.record_match(expr, t)
    for pattern, body in expr.branches:
        names = pattern_vars(pattern)
        for name in names:
            if names.count(name) > 1:
                raise TypeCheckError(
                    "PVar", f"{name} is bound twice in {show_pattern(pattern)}"
                )
        marker = fresh("m")
        branch = f"checking the branch {show_pattern(pattern)} -> {show_expr(body)}"
        with rule_frame("Match", branch):
            ctx = ctx.extend(CMarker(marker))
            ctx = check_pattern(ctx, pattern, ctx.apply(t))
            ctx = check(ctx, body, ctx.apply(expected_type))
            ctx = ctx.drop(CMarker(marker))
    return ctx


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
            with rule_frame(
                "→App",
                f"applying a function of type {show_type(fn_type)} to {show_expr(arg)}",
            ):
                return result, check(ctx, arg, param)
    raise TypeCheckError(
        "→App",
        f"cannot apply a value of type {show_type(fn_type)} to {show_expr(arg)}:"
        " it isn't a function",
    )


def _exists_in(t: Type) -> list[str]:
    """Existentials in `t`, in order of first appearance, without repeats."""
    match t:
        case Exists(name):
            return [name]
        case FunType(param, result):
            return list(dict.fromkeys(_exists_in(param) + _exists_in(result)))
        case TCon(_, args):
            return list(dict.fromkeys(n for arg in args for n in _exists_in(arg)))
        case Forall(_, body):
            return _exists_in(body)
    return []


def _tvars_in(t: Type) -> set[str]:
    match t:
        case TVar(name):
            return {name}
        case FunType(param, result):
            return _tvars_in(param) | _tvars_in(result)
        case TCon(_, args):
            return set().union(*(_tvars_in(arg) for arg in args))
        case Forall(var, body):
            return {var} | _tvars_in(body)
    return set()


def _type_var_names():
    """a, b, ..., z, a1, b1, ..."""
    for n in count():
        for c in "abcdefghijklmnopqrstuvwxyz":
            yield c if n == 0 else f"{c}{n}"


def generalize(ctx: Context, t: Type) -> Type:
    """Close over the existentials still unsolved after checking a program.

    The program was checked in an empty context, so nothing outside it can
    constrain them: `/x -> x` synthesizes ^a -> ^a, which generalizes to
    forall a. a -> a. Names are picked in order of appearance, skipping any
    already used by the type.
    """
    t = ctx.apply(t)
    taken = _tvars_in(t)
    names = (n for n in _type_var_names() if n not in taken)
    chosen = []
    for ex in _exists_in(t):
        name = next(names)
        chosen.append(name)
        t = _replace_exists(t, ex, TVar(name))
    for name in reversed(chosen):
        t = Forall(name, t)
    return t


def _replace_exists(t: Type, name: str, replacement: Type) -> Type:
    match t:
        case Exists(n) if n == name:
            return replacement
        case FunType(param, result):
            return FunType(
                _replace_exists(param, name, replacement),
                _replace_exists(result, name, replacement),
            )
        case TCon(con, args):
            return TCon(
                con, tuple(_replace_exists(arg, name, replacement) for arg in args)
            )
        case Forall(var, body):
            return Forall(var, _replace_exists(body, name, replacement))
    return t


def typecheck_expr(
    expr: Expr,
    env: dict[str, Type] | None = None,
    table: TypeTable | None = None,
) -> Type:
    """Synthesize the type of a whole program, generalized.

    `env` gives the closed types of names defined earlier, e.g. in the REPL,
    and `table` the declared types.
    """
    reset_fresh()
    ctx = Context(table=table or TypeTable())
    ctx = ctx.extend(*(CVar(n, t) for n, t in (env or {}).items()))
    t, delta = synth(ctx, expr)
    check_matches(delta)
    return generalize(delta, t)


def check_matches(ctx: Context):
    """Check every recorded match for missing cases, now that the final
    context has solved as much of each scrutinee's type as it ever will."""
    for match, t in ctx.matches:
        t = ctx.apply(t)
        missing = missing_case(ctx.table, t, [p for p, _ in match.branches])
        if missing is not None:
            raise TypeCheckError(
                "Match",
                f"match {show_expr(match.scrutinee)} with ... doesn't cover every"
                f" {show_type(t)}; missing: {show_pattern(missing)}",
            )


def typecheck_definition(
    d: Definition, env: dict[str, Type], table: TypeTable
) -> Type:
    """The closed type of a top-level definition. It's checked like a whole
    program, so leftover existentials are generalized; only lets inside an
    expression stay monomorphic."""
    if d.rec:
        # The annotation is required, so the recursive use can be given it.
        return typecheck_expr(Anno(d.value, d.type), {**env, d.name: d.type}, table)
    value = d.value if d.type is None else Anno(d.value, d.type)
    return typecheck_expr(value, env, table)


def typecheck_program(
    program: Program,
    table: TypeTable | None = None,
    env: dict[str, Type] | None = None,
) -> tuple[TypeTable, dict[str, Type], Type | None]:
    """Check every item in order. Returns the final table, the types of the
    definitions, and the type of the final expression if there is one."""
    table = table or TypeTable()
    env = dict(env or {})
    for item in program.items:
        match item:
            case DeclGroup():
                table = declare_group(table, item)
            case Definition(name):
                env[name] = typecheck_definition(item, env, table)
    if program.expr is None:
        return table, env, None
    return table, env, typecheck_expr(program.expr, env, table)


def typecheck(src: str) -> Type:
    """The type of a program's final expression, or of `main` if it has
    none."""
    _, env, t = typecheck_program(Parser(lex(src)).parse_program())
    if t is None:
        if "main" not in env:
            raise TypeCheckError("Program", "nothing to check: no final expression or main")
        t = env["main"]
    return t
