import unittest
from lexer import lex
from parser import Parser, IntType, FunType, TVar, Forall, Exists
from context import (
    is_monotype,
    occurs,
    substitute,
    show_type,
    fresh,
    Context,
    CVar,
    CTVar,
    CExists,
    CSolved,
    CMarker,
)

INT = IntType()


def parse_type(src):
    return Parser(lex(src)).parse_type()


class TestTypeOperations(unittest.TestCase):
    def test_monotypes(self):
        self.assertTrue(is_monotype(INT))
        self.assertTrue(is_monotype(FunType(TVar("a"), Exists("b"))))

    def test_forall_is_not_monotype(self):
        self.assertFalse(is_monotype(Forall("a", TVar("a"))))
        self.assertFalse(is_monotype(FunType(INT, Forall("a", TVar("a")))))

    def test_occurs(self):
        self.assertTrue(occurs("a", FunType(INT, Exists("a"))))
        self.assertTrue(occurs("a", Forall("b", Exists("a"))))
        self.assertFalse(occurs("a", FunType(TVar("a"), Exists("b"))))

    def test_substitute(self):
        t = FunType(TVar("a"), FunType(TVar("b"), TVar("a")))
        self.assertEqual(
            substitute(t, "a", Exists("c")),
            FunType(Exists("c"), FunType(TVar("b"), Exists("c"))),
        )

    def test_substitute_stops_at_shadowing_forall(self):
        t = FunType(TVar("a"), Forall("a", TVar("a")))
        self.assertEqual(
            substitute(t, "a", INT), FunType(INT, Forall("a", TVar("a")))
        )

    def test_show_type(self):
        self.assertEqual(show_type(FunType(INT, FunType(INT, INT))), "Int -> Int -> Int")
        self.assertEqual(show_type(FunType(FunType(INT, INT), INT)), "(Int -> Int) -> Int")
        self.assertEqual(show_type(FunType(Exists("a"), TVar("b"))), "^a -> b")

    def test_show_type_forall(self):
        self.assertEqual(
            show_type(Forall("a", FunType(TVar("a"), TVar("a")))), "forall a. a -> a"
        )
        self.assertEqual(
            show_type(FunType(Forall("a", TVar("a")), INT)), "(forall a. a) -> Int"
        )

    def test_show_type_round_trips_through_parser(self):
        for src in [
            "Int",
            "(Int -> Int) -> Int",
            "forall a. forall b. (a -> b) -> a -> b",
            "(forall a. a -> a) -> Int",
        ]:
            t = parse_type(src)
            self.assertEqual(parse_type(show_type(t)), t)

    def test_fresh_names_are_distinct(self):
        self.assertNotEqual(fresh(), fresh())

    def test_fresh_from_fresh_name_keeps_root(self):
        self.assertRegex(fresh(fresh("b")), r"^b'\d+$")


class TestContext(unittest.TestCase):
    def test_extend_does_not_mutate(self):
        gamma = Context()
        delta = gamma.extend(CVar("x", INT))
        self.assertEqual(gamma.entries, ())
        self.assertEqual(delta.entries, (CVar("x", INT),))

    def test_lookup_rightmost_wins(self):
        ctx = Context().extend(CVar("x", INT), CVar("x", TVar("a")))
        self.assertEqual(ctx.lookup("x"), TVar("a"))
        self.assertIsNone(ctx.lookup("y"))

    def test_apply(self):
        # ^a = ^b -> Int, ^b = Int, so [Γ](^a -> ^c) = (Int -> Int) -> ^c
        ctx = Context().extend(
            CExists("c"),
            CSolved("b", INT),
            CSolved("a", FunType(Exists("b"), INT)),
        )
        self.assertEqual(
            ctx.apply(FunType(Exists("a"), Exists("c"))),
            FunType(FunType(INT, INT), Exists("c")),
        )

    def test_apply_under_forall(self):
        ctx = Context().extend(CSolved("a", INT))
        self.assertEqual(
            ctx.apply(Forall("b", FunType(TVar("b"), Exists("a")))),
            Forall("b", FunType(TVar("b"), INT)),
        )

    def test_well_formed(self):
        ctx = Context().extend(CTVar("a"), CExists("b"), CSolved("c", INT))
        self.assertTrue(ctx.well_formed(FunType(TVar("a"), Exists("b"))))
        self.assertTrue(ctx.well_formed(Exists("c")))
        self.assertTrue(ctx.well_formed(Forall("d", FunType(TVar("d"), TVar("a")))))

    def test_not_well_formed(self):
        ctx = Context().extend(CTVar("a"))
        self.assertFalse(ctx.well_formed(TVar("b")))
        self.assertFalse(ctx.well_formed(Exists("a")))
        # a term variable doesn't bind a type variable
        self.assertFalse(Context().extend(CVar("a", INT)).well_formed(TVar("a")))

    def test_forall_binding_does_not_leak(self):
        t = FunType(Forall("a", TVar("a")), TVar("a"))
        self.assertFalse(Context().well_formed(t))

    def test_drop(self):
        ctx = Context().extend(
            CVar("x", INT), CMarker("a"), CExists("a"), CVar("y", Exists("a"))
        )
        self.assertEqual(ctx.drop(CMarker("a")).entries, (CVar("x", INT),))
        self.assertEqual(len(ctx.entries), 4)

    def test_drop_missing_entry_fails(self):
        with self.assertRaises(TypeError):
            Context().drop(CTVar("a"))

    def test_split_arrow(self):
        gamma = Context().extend(CTVar("x"), CExists("a"), CVar("y", INT))
        delta, a1, a2 = gamma.split_arrow("a")
        self.assertEqual(
            delta.entries,
            (
                CTVar("x"),
                CExists(a2.name),
                CExists(a1.name),
                CSolved("a", FunType(a1, a2)),
                CVar("y", INT),
            ),
        )
        self.assertEqual(delta.apply(Exists("a")), FunType(a1, a2))
        self.assertEqual(gamma.entries[1], CExists("a"))

    def test_split_arrow_on_solved_fails(self):
        with self.assertRaises(TypeError):
            Context().extend(CSolved("a", INT)).split_arrow("a")

    def test_str(self):
        ctx = Context().extend(
            CVar("x", INT), CTVar("a"), CMarker("b"), CExists("b"), CSolved("c", INT)
        )
        self.assertEqual(str(ctx), "x : Int, a, |>^b, ^b, ^c = Int")


if __name__ == "__main__":
    unittest.main()
