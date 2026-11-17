TESTS := $(wildcard hooks/*.test.py skills/*/scripts/*.test.py)

.PHONY: test $(TESTS)

test: $(TESTS)

$(TESTS):
	python3 $@
