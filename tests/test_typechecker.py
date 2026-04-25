import unittest
from type_checker import synth, check, IntType, FunType
from parser import IntLit, Add, Lam, Var

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

if __name__ == "__main__":
    unittest.main()
