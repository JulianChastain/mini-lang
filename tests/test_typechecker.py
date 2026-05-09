import unittest
from type_checker import synth, check, typecheck, IntType, FunType
from parser import IntLit, Add, Lam, Var, Anno

class TestTypeChecker(unittest.TestCase):
    def test_synth_int(self):
        self.assertEqual(synth(IntLit(5), {}), IntType())

    def test_synth_add(self):
        self.assertEqual(synth(Add(IntLit(1), IntLit(2)), {}), IntType())

    def test_check_identity_int_to_int(self):
        # (/x -> x) checked against Int -> Int
        check(Lam("x", Var("x")), {}, FunType(IntType(), IntType()))  # should not raise

    def test_check_identity_against_wrong_type(self):
        with self.assertRaises(TypeError):
            check(Lam("x", Var("x")), {}, IntType())

    def test_synth_annotation(self):
        int_to_int = FunType(IntType(), IntType())
        self.assertEqual(synth(Anno(Lam("x", Var("x")), int_to_int), {}), int_to_int)

    def test_synth_annotation_mismatch(self):
        with self.assertRaises(TypeError):
            synth(Anno(IntLit(1), FunType(IntType(), IntType())), {})


class TestTypecheckSource(unittest.TestCase):
    def test_annotated_lambda_applied(self):
        self.assertEqual(typecheck("((/x -> x + 1) : Int -> Int) 2"), IntType())

    def test_annotated_lambda(self):
        self.assertEqual(
            typecheck("((/x -> x + 1) : Int -> Int)"), FunType(IntType(), IntType())
        )

    def test_unannotated_lambda_fails(self):
        with self.assertRaises(TypeError):
            typecheck("(/x -> x + 1) 2")

    def test_bad_annotation_fails(self):
        with self.assertRaises(TypeError):
            typecheck("((/x -> x) : Int)")

    def test_wrong_argument_type_fails(self):
        with self.assertRaises(TypeError):
            typecheck("((/x -> x + 1) : Int -> Int) (/y -> y)")


if __name__ == "__main__":
    unittest.main()
