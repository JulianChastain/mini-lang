import unittest
from lexer import lex
from parser import Parser, IntType, FunType, TVar, Forall, Exists, TCon
from context import Context, CTVar, CExists, CSolved
from subtyping import subtype

INT = IntType()


def parse_type(src):
    return Parser(lex(src)).parse_type()


def is_subtype(a, b, ctx=Context()):
    return subtype(ctx, parse_type(a), parse_type(b))


class TestSubtypingRules(unittest.TestCase):
    def test_var(self):
        ctx = Context().extend(CTVar("a"))
        self.assertEqual(subtype(ctx, TVar("a"), TVar("a")), ctx)

    def test_var_out_of_scope(self):
        with self.assertRaises(TypeError):
            subtype(Context(), TVar("a"), TVar("a"))

    def test_different_vars(self):
        ctx = Context().extend(CTVar("a"), CTVar("b"))
        with self.assertRaises(TypeError):
            subtype(ctx, TVar("a"), TVar("b"))

    def test_int(self):
        self.assertEqual(subtype(Context(), INT, INT), Context())

    def test_exvar(self):
        ctx = Context().extend(CExists("a"))
        self.assertEqual(subtype(ctx, Exists("a"), Exists("a")), ctx)

    def test_arrow(self):
        self.assertEqual(is_subtype("Int -> Int", "Int -> Int"), Context())

    def test_arrow_mismatch(self):
        with self.assertRaises(TypeError):
            is_subtype("Int -> Int", "Int")

    def test_forall_l(self):
        self.assertEqual(is_subtype("forall a. a", "Int"), Context())

    def test_forall_r(self):
        with self.assertRaises(TypeError):
            is_subtype("Int", "forall a. a")

    def test_forall_r_restores_context(self):
        self.assertEqual(is_subtype("forall a. a -> a", "forall b. b -> b"), Context())

    def test_instantiate_l(self):
        ctx = Context().extend(CExists("a"))
        self.assertEqual(
            subtype(ctx, Exists("a"), FunType(INT, INT)).entries,
            (CSolved("a", FunType(INT, INT)),),
        )

    def test_instantiate_r(self):
        ctx = Context().extend(CExists("a"))
        self.assertEqual(subtype(ctx, INT, Exists("a")).entries, (CSolved("a", INT),))

    def test_occurs_check_l(self):
        ctx = Context().extend(CExists("a"))
        with self.assertRaises(TypeError):
            subtype(ctx, Exists("a"), FunType(Exists("a"), INT))

    def test_occurs_check_r(self):
        ctx = Context().extend(CExists("a"))
        with self.assertRaises(TypeError):
            subtype(ctx, FunType(INT, Exists("a")), Exists("a"))


class TestDeclaredTypes(unittest.TestCase):
    def list_of(self, t):
        return TCon("List", (t,))

    def test_same_type(self):
        self.assertEqual(
            subtype(Context(), self.list_of(INT), self.list_of(INT)), Context()
        )

    def test_different_arguments(self):
        with self.assertRaises(TypeError) as caught:
            subtype(Context(), self.list_of(INT), self.list_of(FunType(INT, INT)))
        self.assertEqual(caught.exception.trace[0][0], "<:TCon")

    def test_different_types(self):
        with self.assertRaises(TypeError) as caught:
            subtype(Context(), self.list_of(INT), TCon("Option", (INT,)))
        self.assertEqual(caught.exception.rule, "<:TCon")

    def test_solves_existential_argument(self):
        ctx = Context().extend(CExists("a"))
        delta = subtype(ctx, self.list_of(Exists("a")), self.list_of(INT))
        self.assertEqual(delta.entries, (CSolved("a", INT),))

    def test_forall_instantiates_into_declared_type(self):
        # forall a. List a <: List Int, as Nil checks against List Int
        self.assertEqual(
            subtype(Context(), Forall("a", self.list_of(TVar("a"))), self.list_of(INT)),
            Context(),
        )

    def test_occurs_check_through_declared_type(self):
        ctx = Context().extend(CExists("a"))
        with self.assertRaises(TypeError):
            subtype(ctx, Exists("a"), self.list_of(Exists("a")))


class TestWorkedExamples(unittest.TestCase):
    def test_polymorphic_identity_is_subtype_of_int_identity(self):
        self.assertEqual(is_subtype("forall a. a -> a", "Int -> Int"), Context())

    def test_int_identity_is_not_subtype_of_polymorphic_identity(self):
        with self.assertRaises(TypeError):
            is_subtype("Int -> Int", "forall a. a -> a")

    def test_contravariant_polymorphic_parameter(self):
        is_subtype("(Int -> Int) -> Int", "(forall a. a -> a) -> Int")
        with self.assertRaises(TypeError):
            is_subtype("(forall a. a -> a) -> Int", "(Int -> Int) -> Int")

    def test_more_general_forall(self):
        is_subtype("forall a. forall b. a -> b", "forall c. c -> c")
        with self.assertRaises(TypeError):
            is_subtype("forall c. c -> c", "forall a. forall b. a -> b")

    def test_does_not_mutate_input(self):
        ctx = Context().extend(CExists("a"))
        subtype(ctx, INT, Exists("a"))
        self.assertEqual(ctx.entries, (CExists("a"),))


if __name__ == "__main__":
    unittest.main()
