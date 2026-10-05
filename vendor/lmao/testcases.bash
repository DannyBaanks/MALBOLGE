#!/bin/bash
#
# LMAO test suite
#
# Builds LMAO from source, compiles all example HeLL programs, and verifies
# their output against known-correct results.  Also tests the -f (fast) and
# -d (debug) options.
#
# Requirements: malbolge interpreter on PATH, xxd
#
# Exit status: 0 if all tests passed, non-zero otherwise.

set -u

LMAO=./lmao
MALBOLGE=malbolge
XXD="xxd -p"

PASS=0
FAIL=0

# --------------------------------------------------------------------------
# Helper: run one test case.
#
#   check <description> <actual> <expected>
# --------------------------------------------------------------------------
check() {
    local desc="$1"
    local actual="$2"
    local expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc"
        echo "        expected: $(echo "$expected" | head -c 80)"
        echo "        actual:   $(echo "$actual"   | head -c 80)"
        FAIL=$((FAIL + 1))
    fi
}

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
echo "=== Build ==="
rm -f ./*.mb ./*.bin "$LMAO"
make clean -s
make -s
echo "  Build successful."
echo ""

# --------------------------------------------------------------------------
# Compile all example programs
# --------------------------------------------------------------------------
echo "=== Compile examples ==="
compile_example() {
    local src="$1"
    shift
    "$LMAO" "$@" "$src" 2>&1
}

compile_example example_simple_hello_world.hell
compile_example example_hello_world.hell
compile_example example_simple_cat.hell
compile_example example_cat_halt_on_eof.hell
compile_example example_digital_root.hell
compile_example example_adder.hell
echo "  All examples compiled."
echo ""

# --------------------------------------------------------------------------
# Test: simple Hello World (non-loop version)
# --------------------------------------------------------------------------
echo "=== example_simple_hello_world ==="
check "text output" \
    "$($MALBOLGE example_simple_hello_world.mb)" \
    "Hello, World!"
check "hex output (includes newline)" \
    "$($MALBOLGE example_simple_hello_world.mb | $XXD)" \
    "48656c6c6f2c20576f726c64210a"

# --------------------------------------------------------------------------
# Test: Hello World with loops
# --------------------------------------------------------------------------
echo "=== example_hello_world ==="
check "text output" \
    "$($MALBOLGE example_hello_world.mb)" \
    "Hello, World!"
check "hex output (includes newline)" \
    "$($MALBOLGE example_hello_world.mb | $XXD)" \
    "48656c6c6f2c20576f726c64210a"

# --------------------------------------------------------------------------
# Test: simple cat (infinite echo loop)
#
# Feed 2048 random bytes and verify the first 2048 output bytes are identical.
# The remaining 1024 output bytes should be 0xa8 (C2 mod 256 = 168 = 0xa8),
# because after EOF Malbolge sets A = C2, and the Out instruction outputs
# A mod 256 indefinitely.
# --------------------------------------------------------------------------
echo "=== example_simple_cat ==="
head -c 2048 /dev/urandom > /tmp/lmao_test_rand.bin
# Run the infinite-loop cat through head; suppress SIGPIPE exit code.
{ $MALBOLGE example_simple_cat.mb </tmp/lmao_test_rand.bin || true; } \
    | head -c 3072 > /tmp/lmao_test_out.bin
check "first 2048 bytes match input" \
    "$(diff /tmp/lmao_test_rand.bin <(head -c 2048 /tmp/lmao_test_out.bin))" \
    ""
check "trailing bytes are 0xa8 (A = C2 after EOF)" \
    "$(tail -c 1024 /tmp/lmao_test_out.bin | $XXD | grep -o '..' | grep -v a8)" \
    ""
rm -f /tmp/lmao_test_rand.bin /tmp/lmao_test_out.bin

# --------------------------------------------------------------------------
# Test: cat halting on EOF
# --------------------------------------------------------------------------
echo "=== example_cat_halt_on_eof ==="
head -c 2048 /dev/urandom > /tmp/lmao_test_rand.bin
$MALBOLGE example_cat_halt_on_eof.mb </tmp/lmao_test_rand.bin > /tmp/lmao_test_out.bin
check "output matches input exactly" \
    "$(diff /tmp/lmao_test_rand.bin /tmp/lmao_test_out.bin)" \
    ""
rm -f /tmp/lmao_test_rand.bin /tmp/lmao_test_out.bin

# --------------------------------------------------------------------------
# Test: digital root
# --------------------------------------------------------------------------
echo "=== example_digital_root ==="
check "empty input → 0"     "$(echo ""              | $MALBOLGE example_digital_root.mb)" "0"
check "0 → 0"               "$(echo "0"             | $MALBOLGE example_digital_root.mb)" "0"
check "non-digits ignored"  "$(echo "xxx0aaa"       | $MALBOLGE example_digital_root.mb)" "0"
check "1 → 1"               "$(echo "1"             | $MALBOLGE example_digital_root.mb)" "1"
check "11 → 2"              "$(echo "11"            | $MALBOLGE example_digital_root.mb)" "2"
check "99999999999 → 9"     "$(echo "99999999999"   | $MALBOLGE example_digital_root.mb)" "9"
check "1337 → 5"            "$(echo "1337"          | $MALBOLGE example_digital_root.mb)" "5"

# --------------------------------------------------------------------------
# Test: adder
# --------------------------------------------------------------------------
echo "=== example_adder ==="
check "0 + 0 = 0"        "$(echo "0 0"      | $MALBOLGE example_adder.mb)" "0"
check "1 + 0 = 1"        "$(echo "1 0"      | $MALBOLGE example_adder.mb)" "1"
check "0 + 1 = 1"        "$(echo "0 1"      | $MALBOLGE example_adder.mb)" "1"
check "1 + 1 = 2"        "$(echo "1 1"      | $MALBOLGE example_adder.mb)" "2"
check "999 + 2 = 1001"   "$(echo "999 2"    | $MALBOLGE example_adder.mb)" "1001"
check "222111 + 555"     "$(echo "222111 555" | $MALBOLGE example_adder.mb)" "666"

# --------------------------------------------------------------------------
# Test: -f (fast mode)
# --------------------------------------------------------------------------
echo "=== fast mode (-f) ==="
"$LMAO" -f -o /tmp/lmao_fast_hw.mb example_simple_hello_world.hell 2>/dev/null
check "fast mode: Hello World" \
    "$($MALBOLGE /tmp/lmao_fast_hw.mb)" \
    "Hello, World!"
"$LMAO" -f -o /tmp/lmao_fast_cat.mb example_cat_halt_on_eof.hell 2>/dev/null
head -c 256 /dev/urandom > /tmp/lmao_test_rand.bin
$MALBOLGE /tmp/lmao_fast_cat.mb </tmp/lmao_test_rand.bin > /tmp/lmao_test_out.bin
check "fast mode: cat_halt_on_eof" \
    "$(diff /tmp/lmao_test_rand.bin /tmp/lmao_test_out.bin)" \
    ""
rm -f /tmp/lmao_fast_hw.mb /tmp/lmao_fast_cat.mb \
      /tmp/lmao_test_rand.bin /tmp/lmao_test_out.bin

# --------------------------------------------------------------------------
# Test: -d (debug output)
# --------------------------------------------------------------------------
echo "=== debug output (-d) ==="
"$LMAO" -d -o /tmp/lmao_dbg.mb example_simple_hello_world.hell 2>/dev/null
check "debug: .mb file exists and is non-empty" \
    "$([ -s /tmp/lmao_dbg.mb ] && echo yes || echo no)" \
    "yes"
check "debug: .dbg file exists and is non-empty" \
    "$([ -s /tmp/lmao_dbg.dbg ] && echo yes || echo no)" \
    "yes"
check "debug: .dbg contains :LABELS: section" \
    "$(grep -c ':LABELS:' /tmp/lmao_dbg.dbg)" \
    "1"
check "debug: .dbg contains :SOURCEPOSITIONS: section" \
    "$(grep -c ':SOURCEPOSITIONS:' /tmp/lmao_dbg.dbg)" \
    "1"
check "debug: assembled program still runs correctly" \
    "$($MALBOLGE /tmp/lmao_dbg.mb)" \
    "Hello, World!"
rm -f /tmp/lmao_dbg.mb /tmp/lmao_dbg.dbg

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
echo ""
echo "=== Summary ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "SOME TESTS FAILED."
    exit 1
else
    echo "All tests passed."
    exit 0
fi
