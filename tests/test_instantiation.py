import unittest
from parser import IntType, FunType, TVar, Forall, Exists, TCon
from context import Context, CVar, CTVar, CExists, CSolved
from instantiation import inst_l, inst_r

INT = IntType()


class TestInstL(unittest.TestCase):
    def test_solve(self):
        ctx = Context().extend(CVar("x", INT), CExists("a"), CTVar("b"))
        self.assertEqual(
            inst_l(ctx, "a", FunType(INT, INT)).entries,
            (CVar("x", INT), CSolved("a", FunType(INT, INT)), CTVar("b")),
        )

    def test_solve_to_earlier_existential(self):
        ctx = Context().extend(CExists("b"), CExists("a"))
        self.assertEqual(
            inst_l(ctx, "a", Exists("b")).entries,
            (CExists("b"), CSolved("a", Exists("b"))),
        )

    def test_reach(self):
        ctx = Context().extend(CExists("a"), CExists("b"))
        self.assertEqual(
            inst_l(ctx, "a", Exists("b")).entries,
            (CExists("a"), CSolved("b", Exists("a"))),
        )

    def test_arr(self):
        # ^b is to the right of ^a, so ^a :≤= ^b -> Int can't solve directly
        ctx = Context().extend(CExists("a"), CExists("b"))
        delta = inst_l(ctx, "a", FunType(Exists("b"), INT))
        a = delta.apply(Exists("a"))
        self.assertIsInstance(a, FunType)
        self.assertEqual(a.result, INT)
        self.assertEqual(delta.apply(Exists("b")), a.param)
        self.assertTrue(delta.well_formed(a))

    def test_arr_with_polymorphic_parameter(self):
        # ^a :≤= (forall b. b) -> Int  gives  ^a = ^a1 -> Int
        ctx = Context().extend(CExists("a"))
        delta = inst_l(ctx, "a", FunType(Forall("b", TVar("b")), INT))
        a = delta.apply(Exists("a"))
        self.assertIsInstance(a, FunType)
        self.assertIsInstance(a.param, Exists)
        self.assertEqual(a.result, INT)

    def test_all_r(self):
        ctx = Context().extend(CExists("a"))
        delta = inst_l(ctx, "a", Forall("b", INT))
        self.assertEqual(delta.entries, (CSolved("a", INT),))

    def test_all_r_does_not_leak_bound_variable(self):
        # ^a can't become b, since b is only in scope under the forall
        ctx = Context().extend(CExists("a"))
        with self.assertRaises(TypeError):
            inst_l(ctx, "a", Forall("b", FunType(TVar("b"), TVar("b"))))

    def test_all_r_with_shadowed_name(self):
        ctx = Context().extend(CTVar("b"), CExists("a"))
        delta = inst_l(ctx, "a", Forall("b", INT))
        self.assertEqual(delta.entries, (CTVar("b"), CSolved("a", INT)))

    def test_out_of_scope_type_variable(self):
        ctx = Context().extend(CExists("a"), CTVar("b"))
        with self.assertRaises(TypeError):
            inst_l(ctx, "a", TVar("b"))

    def test_solved_existential_fails(self):
        ctx = Context().extend(CSolved("a", INT))
        with self.assertRaises(TypeError):
            inst_l(ctx, "a", INT)

    def test_does_not_mutate_input(self):
        ctx = Context().extend(CExists("a"))
        inst_l(ctx, "a", INT)
        self.assertEqual(ctx.entries, (CExists("a"),))


class TestInstTCon(unittest.TestCase):
    def setUp(self):
        from lexer import lex
        from parser import Parser
        from types_table import declare_group

        (group,) = Parser(
            lex("type List a = Nil | Cons a (List a)  type Pair a b = Pair a b")
        ).parse_program().items
        self.base = Context(table=declare_group(Context().table, group))

    def test_solve_declared_type_directly(self):
        ctx = self.base.extend(CExists("a"))
        t = TCon("List", (INT,))
        self.assertEqual(inst_l(ctx, "a", t).entries, (CSolved("a", t),))

    def test_inst_l_splits_into_declared_type(self):
        # ^b is right of ^a, so ^a :≤= Pair ^b Int splits ^a into Pair ^a1 ^a2
        ctx = self.base.extend(CExists("a"), CExists("b"))
        delta = inst_l(ctx, "a", TCon("Pair", (Exists("b"), INT)))
        a = delta.apply(Exists("a"))
        self.assertEqual(a.name, "Pair")
        self.assertIsInstance(a.args[0], Exists)
        self.assertEqual(a.args[1], INT)
        self.assertEqual(delta.apply(Exists("b")), a.args[0])

    def test_inst_r_splits_into_declared_type(self):
        ctx = self.base.extend(CExists("a"), CExists("b"))
        delta = inst_r(ctx, TCon("List", (Exists("b"),)), "a")
        a = delta.apply(Exists("a"))
        self.assertEqual(a.name, "List")
        self.assertEqual(delta.apply(Exists("b")), a.args[0])

    def test_split_rejects_out_of_scope_argument(self):
        ctx = self.base.extend(CExists("a"), CTVar("b"))
        with self.assertRaises(TypeError):
            inst_l(ctx, "a", TCon("List", (TVar("b"),)))


class TestInstR(unittest.TestCase):
    def test_solve(self):
        ctx = Context().extend(CExists("a"), CVar("x", INT))
        self.assertEqual(
            inst_r(ctx, INT, "a").entries, (CSolved("a", INT), CVar("x", INT))
        )

    def test_reach(self):
        ctx = Context().extend(CExists("a"), CExists("b"))
        self.assertEqual(
            inst_r(ctx, Exists("b"), "a").entries,
            (CExists("a"), CSolved("b", Exists("a"))),
        )

    def test_arr(self):
        ctx = Context().extend(CExists("a"), CExists("b"))
        delta = inst_r(ctx, FunType(INT, Exists("b")), "a")
        a = delta.apply(Exists("a"))
        self.assertIsInstance(a, FunType)
        self.assertEqual(a.param, INT)
        self.assertEqual(delta.apply(Exists("b")), a.result)
        self.assertTrue(delta.well_formed(a))

    def test_all_l(self):
        # forall b. b -> b =≤: ^a  instantiates b, giving ^a = ^c -> ^c
        ctx = Context().extend(CExists("a"))
        delta = inst_r(ctx, Forall("b", FunType(TVar("b"), TVar("b"))), "a")
        a = delta.apply(Exists("a"))
        self.assertIsInstance(a, FunType)
        self.assertIsInstance(a.param, Exists)
        self.assertEqual(a.param, a.result)
        self.assertTrue(delta.well_formed(a))

    def test_all_l_drops_its_scope(self):
        ctx = Context().extend(CExists("a"))
        delta = inst_r(ctx, Forall("b", INT), "a")
        self.assertEqual(delta.entries, (CSolved("a", INT),))

    def test_arr_rejects_polymorphic_parameter(self):
        # (forall b. b) -> Int <: ^a would need ^a1 <: forall b. b
        ctx = Context().extend(CExists("a"))
        with self.assertRaises(TypeError):
            inst_r(ctx, FunType(Forall("b", TVar("b")), INT), "a")


if __name__ == "__main__":
    unittest.main()
