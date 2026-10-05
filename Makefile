# Requires a Fe compiler built with the `cranelift` feature (native backend).
FE ?= fe
SOURCES = fe.toml $(wildcard ingots/lutz/fe.toml ingots/lutz/src/*.fe tools/decoder/fe.toml tools/decoder/src/*.fe)

out/decoder: $(SOURCES)
	$(FE) build --backend native --ingot decoder --out-dir out .

.PHONY: test
test: out/decoder
	$(FE) test --ingot lutz .
	$(FE) test --backend native --ingot lutz .
	# Needs a checkout of https://github.com/toml-lang/toml-test in TOML_TEST.
	if [ -n "$(TOML_TEST)" ]; then python3 tests/toml_test.py $(TOML_TEST); fi

.PHONY: clean
clean:
	rm -rf out
