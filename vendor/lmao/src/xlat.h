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

#ifndef LMAO_XLAT_H
#define LMAO_XLAT_H

#include "types.h"

/**
 * Returns non-zero if the given Malbolge opcode behaves as a NOP
 * (i.e. is not one of the eight active Malbolge commands).
 *
 * \param command Numeric Malbolge command value (result of (char + position) % 94).
 * \return Non-zero when the command is a NOP; zero otherwise.
 */
int is_nop(int command);

/**
 * Checks whether a given ASCII character may be placed at the given position
 * in the Malbolge source without causing an unwanted active command.
 *
 * \param position Memory address (0-based).
 * \param character Candidate ASCII character (must be in range 33-126).
 * \return Non-zero if the character is safe to use at this position; zero otherwise.
 */
int is_valid_initial_character(int position, char character);

/**
 * Checks whether the given xlat2 cycle is achievable at the given memory position.
 * If it is and start_symbol is non-NULL, the first ASCII character of the cycle
 * is written to *start_symbol.
 *
 * \param cycle    The xlat2 cycle to test (linked list of XlatCycle nodes).
 * \param position Memory address of the first cell of the cycle.
 * \param start_symbol If non-NULL and the cycle exists, receives the starting ASCII character.
 * \return Non-zero when the cycle exists at the given position; zero otherwise.
 */
int is_xlatcycle_existent(XlatCycle *cycle, int position, char *start_symbol);

#endif /* LMAO_XLAT_H */
