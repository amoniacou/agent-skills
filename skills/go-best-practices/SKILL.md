---
name: go-best-practices
description: Best practices for writing Go code. Load it yourself, without being asked, before writing or changing Go code.
when_to_use: Before writing, editing or reviewing a .go file. Also on "golang", "go code", "idiomatic go", "go best practices".
---

# Go best practices

## 1. No reflection when the types are known

When the code knows the types at compile time, write plain code. `reflect` is many times slower, skips the compiler's type checks and hides which fields are used.

- compare two fields with `a.Name == b.Name`, not `reflect.DeepEqual(a.Name, b.Name)`
- compare structs whose fields are all comparable with `a == b`
- compare slices and maps with `slices.Equal` and `maps.Equal`
- branch on a type with a type switch, not `reflect.TypeOf` or `reflect.ValueOf(x).Kind()`
- write a shared function with type parameters, not `any` plus `reflect`
- copy a struct with assignment, not by walking its fields

Use `reflect` only when the type is unknown until runtime and nothing else works: a serializer, a struct-tag parser, an ORM mapper. In tests, `reflect.DeepEqual` and `cmp.Diff` are fine.
