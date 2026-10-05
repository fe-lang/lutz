# lutz

*Lutz unravels TOML zealously.*

A [TOML 1.0](https://toml.io/en/v1.0.0) parser for
[Fe](https://github.com/argotorg/fe) programs. It passes all TOML 1.0 cases of
the [toml-test](https://github.com/toml-lang/toml-test) suite: the 208 valid
documents decode to the expected values and the 501 invalid ones are rejected.

lutz is named in memory of [Lutz Marquardt](https://ebermann-bestattungen.gemeinsam-trauern.net/Begleiten/lutz-marquardt),
a German developer who died far too early, at the age of 36.

## Usage

```toml
# fe.toml, with lutz checked out next to the project
[dependencies]
lutz = { path = "../lutz/ingots/lutz" }
```

```fe
use core::Option
use std::native::ByteBuffer

/// `server.port` of a TOML document, or 0.
fn port(_ source: ByteBuffer) -> i64 {
    let doc = lutz::parse(source, 0, source.len())
    let mut port: i64 = 0
    if doc.ok() {
        let node = entry(doc, entry(doc, doc.root(), "server"), "port")
        if node != lutz::NONE && doc.is_integer(node) {
            port = doc.integer(node)
        }
    }
    doc.release()
    port
}

/// The entry `key` of `table`, or `NONE`.
fn entry<K: lutz::Key>(_ doc: lutz::Document, _ table: u64, _ key: K) -> u64 {
    match doc.get(table, key) {
        Option::Some(node) => node
        Option::None => lutz::NONE
    }
}
```

A document is a tree of nodes addressed by `u64` handles; `lutz::NONE` marks
a missing node. Tables and arrays keep their entries in source order.

| | |
| --- | --- |
| `ok()`, `error()`, `error_offset()`, `push_error(mut out)` | the parse result; `push_error` appends `line <l>, column <c>: <description>` |
| `root()`, `kind(node)`, `is_table` / `is_array` / `is_string` / `is_integer` / `is_boolean` | structure |
| `get(table, "key")`, `len(node)`, `first(node)`, `next(node)`, `at(array, i)` | navigation |
| `key(node)`, `value(node)`, `byte_at(i)`, `push_key`, `push_string` | decoded keys and strings; floats and date-times as normalized text |
| `integer(node)`, `push_integer`, `boolean(node)` | numbers and booleans |
| `release()` | frees the document |

Keys and strings are decoded (escapes, line ending backslashes, CRLF to LF).
Integers are checked to fit 64 bits. Dates and times are validated, including
leap years. Tables follow the definition rules of Python's `tomllib`.

## Design

The whole document lives in one allocation, divided into regions sized from
the source length: the source, the decoded text, the nodes, and the stacks of
key segments and open containers. Arrays and inline tables are parsed with an
explicit stack instead of recursion, so nesting depth is limited by memory
only. Both choices also keep Fe's borrow checking of the parser fast.

## Testing

```sh
make test FE=/path/to/fe                                  # Fe unit tests
make test FE=/path/to/fe TOML_TEST=/path/to/toml-test     # plus the toml-test suite
```

The repository is a Fe workspace: the library is `ingots/lutz`, and
`tools/decoder` is the toml-test decoder: TOML on stdin, tagged JSON on
stdout. `tests/toml_test.py` runs it on the suite with the comparison rules of
toml-test's runner (Go isn't needed).
