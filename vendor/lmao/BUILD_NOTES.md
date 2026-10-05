# LMAO vendored — build notes (Linux, no flex/bison needed)

Copied from `MALBOLGE-MB-DATABASE/third_party/lmao` on 2026-10-02
(Matthias Lutter, LMAO v0.6.0, GPLv3 — see `LICENSE`).

This is the **Classic** Malbolge assembler (10-trit, 59049 cells).
Do not confuse it with LMFAO (`MALDOOM/vendor/LMFAO`), which targets
Malbolge Unshackled.

The pre-generated `bin/lex.yy.c`, `bin/lmao.tab.c` and `bin/lmao.tab.h`
allow building without flex/bison:

```sh
cd vendor/lmao
gcc -O3 -I bin -I src -c bin/lmao.tab.c -o bin/bison.o
gcc -O3 -I bin -I src -c bin/lex.yy.c  -o bin/lex.o
for f in globals xlat label layout prefix debug cli main malbolge initialize gen_init; do
  gcc -O3 -I bin -I src -c src/$f.c -o bin/$f.o
done
gcc bin/*.o -o bin/lmao
```

Compile and run the bundled adder (Classic):

```sh
./bin/lmao -o /tmp/adder.mb example_adder.hell
printf '999 2\n' | python3 -c "
import sys; sys.path.insert(0, '.')
import malbolge
print(malbolge.run(open('/tmp/adder.mb').read(), sys.stdin.buffer.read(), 20_000_000))"
# -> ('HALTED', 253280, b'1001\n')
```

Known quirk: LMAO output is **not byte-reproducible** — `initialize.c`
fills unused cells with `rand() % 8` NOP-class opcodes and `main.c` calls
`srand(time(NULL))`. Two builds differ in ~389 bytes but run identically.
