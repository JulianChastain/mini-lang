# The global table of declared types and their constructors.
from parser import Type, FunType, TVar, Forall, TCon, DeclGroup, TypeDecl, MAX_TUPLE, tuple_name
from context import Context, CTVar, TypeTable, TypeInfo, CtorInfo
from errors import TypeCheckError


def _scheme(name: str, params: tuple[str, ...], fields: tuple[Type, ...]) -> Type:
    """∀params. F1 → … → Fn → T params"""
    t: Type = TCon(name, tuple(TVar(p) for p in params))
    for f in reversed(fields):
        t = FunType(f, t)
    for p in reversed(params):
        t = Forall(p, t)
    return t


def builtin_table() -> TypeTable:
    """The table every program starts from: the tuple types, each
    declared as `type TupleN a b ... = TupleN a b ...`."""
    decls = []
    for n in range(2, MAX_TUPLE + 1):
        params = tuple("abcdefg"[:n])
        name = tuple_name(n)
        decls.append(TypeDecl(name, params, ((name, tuple(TVar(p) for p in params)),)))
    return declare_group(TypeTable(), DeclGroup(tuple(decls)))


def declare_group(table: TypeTable, group: DeclGroup) -> TypeTable:
    """Add a group of declarations, returning the new table.

    Every type in the group is registered before any constructor field is
    checked, so the types can refer to each other (and themselves).
    """
    types = dict(table.types)
    ctors = dict(table.ctors)
    for decl in group.decls:
        if decl.name in types:
            raise TypeCheckError("Decl", f"type {decl.name} is already declared")
        if len(set(decl.params)) != len(decl.params):
            raise TypeCheckError(
                "Decl", f"type {decl.name} repeats a type parameter"
            )
        types[decl.name] = TypeInfo(
            decl.params, tuple(name for name, _ in decl.constructors)
        )

    new_table = TypeTable(types, ctors)
    for decl in group.decls:
        scope = Context(table=new_table).extend(*(CTVar(p) for p in decl.params))
        for con, fields in decl.constructors:
            if con in ctors:
                raise TypeCheckError("Decl", f"constructor {con} is already declared")
            for f in fields:
                if reason := scope.why_ill_formed(f):
                    if reason.startswith("type variable"):
                        reason += f" (it isn't a parameter of {decl.name})"
                    raise TypeCheckError("Decl", f"in constructor {con}: {reason}")
            ctors[con] = CtorInfo(decl.name, fields, _scheme(decl.name, decl.params, fields))
    return new_table
