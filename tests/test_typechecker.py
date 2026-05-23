import unittest
from type_checker import synth, check, app_synth, typecheck, show_expr, IntType, FunType
from lexer import lex
from parser import Parser
from parser import IntLit, Add, Lam, Var, Anno, TVar, Forall, Exists
from context import Context, CVar, CTVar, CExists

INT = IntType()


class TestTypeChecker(unittest.TestCase):
    def test_synth_int(self):
        self.assertEqual(synth(Context(), IntLit(5)), (INT, Context()))

    def test_synth_add(self):
        self.assertEqual(synth(Context(), Add(IntLit(1), IntLit(2))), (INT, Context()))

    def test_synth_var(self):
        ctx = Context().extend(CVar("x", INT))
        self.assertEqual(synth(ctx, Var("x")), (INT, ctx))

    def test_synth_unbound_var(self):
        with self.assertRaises(TypeError):
            synth(Context(), Var("x"))

    def test_check_identity_int_to_int(self):
        # (/x -> x) checked against Int -> Int
        ctx = check(Context(), Lam("x", Var("x")), FunType(INT, INT))
        self.assertEqual(ctx, Context())

    def test_check_identity_against_wrong_type(self):
        with self.assertRaises(TypeError):
            check(Context(), Lam("x", Var("x")), INT)

    def test_check_shadowed_lambda_restores_context(self):
        # /x -> /x -> x pushes x : Int twice; leaving the inner scope must
        # keep the outer one
        expr = Lam("x", Lam("x", Var("x")))
        self.assertEqual(
            check(Context(), expr, FunType(INT, FunType(INT, INT))), Context()
        )

    def test_check_forall(self):
        identity = Forall("a", FunType(TVar("a"), TVar("a")))
        self.assertEqual(check(Context(), Lam("x", Var("x")), identity), Context())

    def test_check_forall_rejects_too_specific(self):
        identity = Forall("a", FunType(TVar("a"), TVar("a")))
        with self.assertRaises(TypeError):
            check(Context(), Lam("x", Add(Var("x"), IntLit(1))), identity)

    def test_check_forall_with_shadowed_type_variable(self):
        # The inner annotation's `a` refers to the inner forall's a.
        ctx = Context().extend(CTVar("a"))
        expr = Lam("x", Anno(Var("x"), TVar("a")))
        identity = Forall("a", FunType(TVar("a"), TVar("a")))
        self.assertEqual(check(ctx, expr, identity), ctx)

    def test_synth_annotation(self):
        int_to_int = FunType(INT, INT)
        t, _ = synth(Context(), Anno(Lam("x", Var("x")), int_to_int))
        self.assertEqual(t, int_to_int)

    def test_synth_annotation_mismatch(self):
        with self.assertRaises(TypeError):
            synth(Context(), Anno(IntLit(1), FunType(INT, INT)))

    def test_synth_annotation_not_well_formed(self):
        with self.assertRaises(TypeError):
            synth(Context(), Anno(IntLit(1), TVar("a")))

    def test_synth_lambda(self):
        # →I⇒: /x -> x + 1 synthesizes ^a -> ^b with both solved to Int
        t, ctx = synth(Context(), Lam("x", Add(Var("x"), IntLit(1))))
        self.assertEqual(ctx.apply(t), FunType(INT, INT))

    def test_synth_lambda_leaves_existentials_in_context(self):
        t, ctx = synth(Context(), Lam("x", Var("x")))
        self.assertIsInstance(t.param, Exists)
        self.assertTrue(ctx.well_formed(t))
        self.assertEqual(ctx.apply(t.param), ctx.apply(t.result))

    def test_app_synth_function(self):
        self.assertEqual(
            app_synth(Context(), FunType(INT, INT), IntLit(1)), (INT, Context())
        )

    def test_app_synth_forall(self):
        identity = Forall("a", FunType(TVar("a"), TVar("a")))
        t, ctx = app_synth(Context(), identity, IntLit(1))
        self.assertEqual(ctx.apply(t), INT)

    def test_app_synth_existential(self):
        ctx = Context().extend(CExists("f"))
        t, delta = app_synth(ctx, Exists("f"), IntLit(1))
        self.assertEqual(delta.apply(Exists("f")), FunType(INT, t))

    def test_app_synth_non_function(self):
        with self.assertRaises(TypeError):
            app_synth(Context(), INT, IntLit(1))


class TestShowExpr(unittest.TestCase):
    def test_round_trips_through_parser(self):
        for src in [
            "/x -> x + 1",
            "(/x -> x) y",
            "f x (g y)",
            "1 + (2 + 3)",
            "(/x -> x) + 1",
            "((/x -> x) : forall a. a -> a) 1",
        ]:
            expr = Parser(lex(src))()
            self.assertEqual(Parser(lex(show_expr(expr)))(), expr)
            self.assertEqual(show_expr(expr), src)


class TestTypecheckSource(unittest.TestCase):
    def test_annotated_lambda_applied(self):
        self.assertEqual(typecheck("((/x -> x + 1) : Int -> Int) 2"), INT)

    def test_annotated_lambda(self):
        self.assertEqual(
            typecheck("((/x -> x + 1) : Int -> Int)"), FunType(INT, INT)
        )

    def test_unannotated_lambda(self):
        # →I⇒ lets unannotated lambdas synthesize
        self.assertEqual(typecheck("(/x -> x + 1) 2"), INT)

    def test_unannotated_identity_is_generalized(self):
        self.assertEqual(
            typecheck("/x -> x"), Forall("a", FunType(TVar("a"), TVar("a")))
        )

    def test_bad_annotation_fails(self):
        with self.assertRaises(TypeError):
            typecheck("((/x -> x) : Int)")

    def test_wrong_argument_type_fails(self):
        with self.assertRaises(TypeError):
            typecheck("((/x -> x + 1) : Int -> Int) (/y -> y)")

    def test_polymorphic_identity(self):
        self.assertEqual(typecheck("((/x -> x) : forall a. a -> a) 1"), INT)

    def test_rank_two_accepts_identity(self):
        self.assertEqual(
            typecheck("((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x)"), INT
        )

    def test_rank_two_rejects_non_identity(self):
        with self.assertRaises(TypeError):
            typecheck("((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x + 1)")

    def test_self_application_fails_occurs_check(self):
        with self.assertRaises(TypeError):
            typecheck("/x -> x x")

    def test_self_application_with_rank_two_annotation(self):
        t = typecheck("((/x -> x x) : (forall a. a -> a) -> (forall b. b -> b))")
        self.assertIsInstance(t, FunType)


if __name__ == "__main__":
    unittest.main()
