# LMAO — Low-level Malbolge Assembler, Ooh!

LMAO is an assembler that translates programs written in HeLL (Hellish
Low-level Language) into executable Malbolge programs.

Malbolge is a notoriously difficult esoteric programming language designed by
Ben Olmstead in 1998. Its difficulty comes from its self-modifying instruction
set: every instruction changes itself after execution, so writing Malbolge by
hand is extremely hard. LMAO removes that burden by letting you write in HeLL,
a readable assembly language that maps cleanly to Malbolge's execution model.


## Building

Requirements: gcc, flex, bison, make

    make

The resulting binary is placed at `./lmao`.

To install system-wide (default prefix `/usr`):

    make install

To uninstall:

    make uninstall

To generate Doxygen API documentation (requires doxygen):

    make doc


## Usage

    lmao [options] <input.hell>

Options:

    -o <file>      Write output to <file> (default: replace .hell extension
                   with .mb, or append .mb if no extension is found).
    -f             Fast mode: place the HeLL program at the end of the
                   Malbolge address space. Produces larger output files but
                   compiles faster. Automatically retries in normal mode if
                   a memory conflict occurs.
    -l <number>    Insert a newline after every <number> characters in the
                   output file (useful for editors with line-length limits).
    -d             Write a debug information file alongside the output (same
                   name as the output file with a .dbg extension). The .dbg
                   file is used by HeLL IDE.

Examples:

    lmao example_simple_cat.hell
    lmao -f -o cat.mb example_simple_cat.hell
    lmao -d -o cat.mb example_simple_cat.hell


## HeLL Language Reference

HeLL source files consist of two kinds of sections: `.CODE` and `.DATA`. Both
kinds of sections may appear multiple times and in any order. Within each
section, declarations are grouped into blocks.


### Blocks

A block is a contiguous group of memory cells. Blocks are separated from one
another by a blank line (a line that contains no text, not even a comment).
Alternatively, a block can be explicitly delimited by curly braces `{ }`.

```
.DATA
LABEL1:
42 0 0

LABEL2:
1 2 3

{ LABEL3: 7 8 9 }   ; braces make this a self-contained block
```

Every block must begin with at least one label. Labels are identifiers
(letters, digits, underscore; must start with a letter or underscore) followed
by a colon.


### The .OFFSET Directive

Placing `.OFFSET <value>` or `@<value>` at the start of a block forces its
first cell to the given Malbolge address. Only use this when the exact
position matters (e.g., for the `CARRY` label described below).

```
.CODE
@C21
CARRY: Nop
```


### Comments

```
; line comment
% line comment
# line comment
// line comment
/* multi-line
   comment */
```


### The ENTRY Label

The data section must define a label named `ENTRY`. When the assembled Malbolge
program starts execution, the D register points at the `ENTRY` cell. The C
register points at a `Jmp` instruction. The value of the A register is
unspecified.


### .DATA Section

Each entry in a `.DATA` block is a single memory cell. Its value is an
arithmetic expression that may reference labels.


#### Numeric Constants

```
42          decimal integer (0 – 59048)
0t1210      ternary integer (digits 0-2; up to 10 ternary digits)
'A'         ASCII character literal; escape sequences: \n \r \t \\ \'  \0
C0          0t0000000000 = 0
C1          0t1111111111 = 29524
C2          0t2222222222 = 59048
C20         0t2222222220 = 59046
C21         0t2222222221 = 59047
EOF         synonym for C2 (the value stored in A on end-of-file)
```


#### Arithmetic Operators

Operators are evaluated with standard precedence. Parentheses are supported
for grouping. All values are 10-trit (modulo C2+1 = 59049).

```
a + b       addition
a - b       subtraction
a * b       multiplication
a / b       integer division
a >> n      tritwise rotate right by n positions (0 ≤ n < 10)
a << n      tritwise rotate left  by n positions (0 ≤ n < 10)
a ! b       Malbolge crazy operator (tritwise: see malbolge.h)
```

Example: compute C2 minus 1 using operators:

```
C2 - 1
```


#### Label References

Writing a label name in a `.DATA` cell stores the Malbolge address of that
label minus 1. The minus-1 adjustment compensates for the automatic D-register
increment that Malbolge performs after every instruction: a `Jmp` or `MovD`
that loads this address will therefore land on the correct cell.

```
SOME_LABEL          address of SOME_LABEL minus 1
```


#### R_ Prefix (Successor Reference)

`R_LABEL` is equivalent to `LABEL + 1`, i.e., the address of the cell
immediately following `LABEL`. It is used when a code cell needs to restore
itself by transforming it to the next entry in its xlat2 cycle.

```
R_SOME_LABEL        address of SOME_LABEL (no minus-1 adjustment)
```


#### U_ Prefix (Relative Offset Reference)

`U_TARGET ANCHOR` stores the address of `TARGET` (which must reside in the
`.CODE` section) minus the distance from the current position to `ANCHOR`
(which must follow later in the current `.DATA` section). This is used to
create a destination jump address for the C register that, when the D register
has been incremented to `ANCHOR`, will point exactly at the cell `TARGET`. Any
cells preceding `TARGET` are automatically filled with `RNop` instructions
(see the [`.CODE` section](#code-section) below).

```
.DATA
EXAMPLE:
  U_OPR  VALUE    ; address of OPR minus distance to VALUE, i.e. address of OPR minus 3
  SOME_LABEL
  SOME_OTHER_LABEL
VALUE:
  C1

.CODE
OPR:
  Opr/Nop
  Jmp
```


#### Don't-Care and Unused Markers

```
?           Reserve this cell; its initial value is unimportant.
?-          Mark this cell as unused. LMAO may reuse its address.
            Never write a label before ?- (use ? instead).
```


#### Strings

```
"Hello"             expands to 'H' 'e' 'l' 'l' 'o'
"AB", 0             expands to 'A' 0 'B'  (separator between chars)
```

Supported escape sequences: `\n` `\r` `\t` `\\` `\"` `\0`


### .CODE Section

Each entry in a `.CODE` block is an xlat2 cycle description. An xlat2 cycle
describes how a memory cell's effective Malbolge command changes each time the
cell is executed.


#### Single Command (Non-Loop-Resistant)

A single command that is executed once and then mutates:

```
Jmp
MovD
Opr
Rot
Out
In
Hlt
Nop
```

These cells change their effective opcode every time they execute. In most
HeLL programs each such cell is only executed once. The opcode the cell
transforms into after execution is unspecified.


#### xlat2 Cycle

A sequence of commands separated by `/` describes the complete sequence of
opcodes the cell will produce on successive executions:

```
Jmp/Nop/Nop         ; first execution: Jmp; second: Nop; third: Nop; repeat
```

The cycle is closed: after the last command, the cell's xlat2-encrypted value
will equal the first command again. Note that some xlat2 cycles are impossible
in Malbolge; LMAO will report an error if this is the case.


#### RNop (Loop-Resistant NOP)

```
RNop                ; abbreviation for Nop/Nop
```

A loop-resistant NOP is a cell that acts as a `Nop` on every execution. It is
guaranteed to exist at every memory position.


### How LMAO Assembles a HeLL Program

LMAO translates a HeLL source file in several phases:

1. **Parsing**: The lexer/parser reads the source and builds internal
   representations of all `.CODE` and `.DATA` blocks, with labels resolved to
   block pointers.

2. **Prefix resolution**: `U_` references are resolved; virtual `RNop`
   cells are synthesized before referenced code blocks as needed.

3. **Memory layout**: Each block is assigned an absolute Malbolge address.
   Code blocks are placed at positions that satisfy the xlat2 position
   constraint (the start character must be in ASCII range 33–126 and encode
   the correct opcode for that address). Blocks with explicit `.OFFSET`
   directives are placed first.

4. **Initialization code generation**: LMAO generates a sequence of Malbolge
   instructions that writes every `.DATA` and runtime-initialized `.CODE` cell
   to its desired value. This sequence uses a pre-compiled constant-generation
   data module (see `datamodule.txt`) to load arbitrary values into the A
   register, jump to the target addresses, and write the value there via the
   `Opr` instruction.

5. **Output**: The final Malbolge source is written to the output file. The
   pre-compiled code for data module creation is followed by the generated
   instruction sequence and the RQ terminator. The latter ensures that cells
   after the end of the Malbolge program are initialized with the correct
   values by the Malbolge interpreter.


## Example HeLL Programs

The following example programs ship with LMAO, ordered by complexity:

```
example_simple_cat.hell         Infinite echo loop (cat)
example_simple_hello_world.hell Print "Hello, World!\n" (no loops)
example_hello_world.hell        Print "Hello, World!\n" (using loops)
example_cat_halt_on_eof.hell    Cat that halts cleanly on EOF
example_digital_root.hell       Read a decimal number, print its digital root
example_adder.hell              Read two 3-digit numbers, print their sum
```

To compile and run an example (requires a Malbolge interpreter):

    lmao example_simple_cat.hell
    malbolge example_simple_cat.mb


## Further Resources

- [Beginner's tutorial](https://lutter.cc/malbolge/tutorial/cat.html) — walks through `example_simple_cat.hell` step by step
- [HeLL IDE](https://github.com/esoteric-programmer/HeLL-IDE) — graphical debugger for HeLL programs
- [HeLL IDE online](https://dev.lutter.cc/malbolge/WebIDE/)
- [Original Malbolge specification](http://www.lscheffer.com/malbolge_spec.html)


## License

LMAO is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Copyright (C) 2013-2026 Matthias Lutter <matthias@lutter.cc>
