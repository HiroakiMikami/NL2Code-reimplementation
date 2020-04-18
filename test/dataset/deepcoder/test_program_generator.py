import unittest
import numpy as np

from nl2prog.dataset.deepcoder.dsl \
    import Function, Type, Variable, Signature
from nl2prog.dataset.deepcoder.program_generator \
    import arguments, programs, random_programs, IdGenerator


class Test_program_generator(unittest.TestCase):
    def test_arguments(self):
        g = IdGenerator()
        args = list(arguments(g, set([Variable(g.generate(), Type.Int),
                                      Variable(g.generate(), Type.IntList)]),
                              [Type.Int, Type.IntList]))
        """
        [v(0), v(1)]
        [v(0), v_new]
        [v_new, v(1)]
        [v_new1, v_new2]
        """
        self.assertEqual(4, len(args))
        self.assertEqual(2, g.generate())

    def test_arguments_if_arguments_with_same_type(self):
        g = IdGenerator()
        args = list(arguments(g, set(), [Type.Int, Type.Int]))
        """
        [v_new, v_new]
        [v_new1, v_new2]
        """
        self.assertEqual(2, len(args))
        self.assertEqual(0, g.generate())

    def test_arguments_if_no_existing_variables(self):
        # No existing variable
        g = IdGenerator()
        args = list(arguments(g, set(), [Type.Int, Type.IntList]))
        self.assertEqual(1, len(args))
        self.assertEqual([Variable(0, Type.Int), Variable(
            1, Type.IntList)], args[0].arguments)
        self.assertEqual(
            set([Variable(0, Type.Int),
                 Variable(1, Type.IntList)]), args[0].variables)
        self.assertEqual([Variable(0, Type.Int), Variable(
            1, Type.IntList)], args[0].new_variables)
        self.assertEqual(2, args[0].generator.generate())
        self.assertEqual(0, g.generate())

    def test_programs(self):
        TAKE = Function("TAKE", Signature(
            [Type.Int, Type.IntList], Type.IntList))
        HEAD = Function("HEAD", Signature([Type.IntList], Type.Int))
        srcs = set(map(lambda x: x.to_string(),
                       programs([TAKE, HEAD], 1, 1)))
        self.assertEqual(
            set(["a <- int\nb <- [int]\nc <- TAKE a b\n",
                 "a <- [int]\nb <- HEAD a\n"]),
            srcs
        )

        srcs = list(programs([TAKE], 2, 2))
        lengths = set(map(lambda x: len(x.body), srcs))

        self.assertEqual(set([2]), lengths)


class Test_random_programs(unittest.TestCase):
    def test_random_programs(self):
        TAKE = Function("TAKE", Signature(
            [Type.Int, Type.IntList], Type.IntList))
        HEAD = Function("HEAD", Signature([Type.IntList], Type.Int))
        lengths = []
        for _, program in zip(range(100),
                              random_programs([TAKE, HEAD], 1, 2,
                                              rng=np.random.RandomState(100))):
            lengths.append(len(program.body))
        self.assertTrue(min(lengths) >= 1)
        self.assertTrue(max(lengths) >= 2)


if __name__ == "__main__":
    unittest.main()
