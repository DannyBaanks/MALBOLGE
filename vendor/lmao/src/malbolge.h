/*

	This file is part of LMAO (Low-level Malbolge Assembler, Ooh!), an assembler for Malbolge.
	Copyright (C) 2013-2026 Matthias Lutter

	LMAO is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	LMAO is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program. If not, see <http://www.gnu.org/licenses/>.

	E-Mail: matthias@lutter.cc

*/

#ifndef LMAO_MALBOLGE_H
#define LMAO_MALBOLGE_H

/** All-zeros 10-trit value: 0t0000000000 = 0. */
#define C0  0

/** All-ones 10-trit value: 0t1111111111 = 29524. */
#define C1  29524

/** All-twos 10-trit value: 0t2222222222 = 59048. */
#define C2  59048

/** C2 minus 1: 0t2222222221 = 59047. */
#define C21 (C2 - 1)

/**
 * Malbolge opcode for the Nop instruction.
 *
 * Nop has no effect: it leaves all registers unchanged and increments C and D.
 * Any value whose (value + address) % 94 is not one of the other seven opcodes
 * acts as a Nop.  The canonical Nop opcode is 68.
 */
#define MALBOLGE_COMMAND_NOP   68

/**
 * Malbolge opcode for the MovD instruction.
 *
 * Sets D = [D] (loads the value at the address pointed to by D into D itself),
 * then increments C and D.
 */
#define MALBOLGE_COMMAND_MOVED 40

/**
 * Malbolge opcode for the Opr (crazy) instruction.
 *
 * Computes crazy(A, [D]) and stores the result in both A and [D], then
 * increments C and D.
 *
 * \sa crazy()
 */
#define MALBOLGE_COMMAND_OPR   62

/**
 * Malbolge opcode for the Jmp instruction.
 *
 * Sets C = [D], then increments D.
 * (C is not incremented after a Jmp.)
 */
#define MALBOLGE_COMMAND_JMP   4

/**
 * Malbolge opcode for the Rot instruction.
 *
 * Computes rotate_right([D]) and stores the result in both A and [D], then
 * increments C and D.
 *
 * \sa rotate_right()
 */
#define MALBOLGE_COMMAND_ROT   39

/**
 * Malbolge opcode for the Out instruction.
 *
 * Writes (A % 256) as an ASCII character to stdout, then increments C and D.
 */
#define MALBOLGE_COMMAND_OUT   5

/**
 * Malbolge opcode for the In instruction.
 *
 * Reads one ASCII character from stdin into A (0-255), or sets A = C2 on EOF.
 * Then increments C and D.
 */
#define MALBOLGE_COMMAND_IN    23

/**
 * Malbolge opcode for the Hlt instruction.
 *
 * Terminates the program immediately.
 */
#define MALBOLGE_COMMAND_HALT  81

/**
 * The xlat2 self-encryption table used by Malbolge.
 *
 * After every instruction executes, the character at address C is replaced by
 * XLAT2[that_character - 33].  This means a code cell's effective opcode
 * changes every time it is executed, cycling through all 94 printable ASCII
 * characters before returning to the original.
 */
#define XLAT2 "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"

/**
 * Malbolge crazy (tritwise) operator.
 *
 * For each trit position (0-9), the output trit is determined by the lookup
 * table: crz[a_trit + 3 * d_trit], where:
 *   crz = {1, 0, 0,  1, 0, 2,  2, 2, 1}
 *
 * \param a  Value of the A register.
 * \param d  Value of the memory cell [D].
 * \return   crazy(a, d), a 10-trit value in [0, C2].
 */
unsigned int crazy(unsigned int a, unsigned int d);

/**
 * Tritwise rotate-right operation.
 *
 * The least-significant trit of \p d is moved to the most-significant trit
 * position, and all other trits shift one position toward the LSB.  For a
 * 10-trit value this is equivalent to:
 *   result = (d / 3) + (d % 3) * 19683
 *
 * \param d  A 10-trit value in [0, C2].
 * \return   The value of d rotated right by one trit position.
 */
unsigned int rotate_right(unsigned int d);

#endif /* LMAO_MALBOLGE_H */
