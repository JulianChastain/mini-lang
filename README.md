# mini-lang

A tiny ML-style typed functional language. Built as a learning project so I could implement bidirectional typechecking à la Dunfield & Krishnaswami (2013).

## Status

Work in progress. Currently implemented:

- Lexer for the lambda calculus core
- Recursive-descent parser producing an AST

## Roadmap

- [x] Lexer
- [x] Parser (lambda core: variables, lambdas, application)
- [ ] Tree-walking evaluator
- [ ] Hindley-Milner / bidirectional type inference
- [ ] Algebraic data types and pattern matching
- [ ] Polymorphism

## Syntax

Currently the parser accepts the core lambda calculus:

    /x -> x              -- identity function
    (/x -> x) y          -- applied to y
    f x y                -- left-associative application
