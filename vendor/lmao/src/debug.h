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

#ifndef LMAO_DEBUG_H
#define LMAO_DEBUG_H

#include "types.h"
#include "malbolge.h"
#include <stdio.h>

/**
 * Writes a map of Malbolge memory addresses to HeLL source positions.
 * One line per used memory cell: "<address>: CODE|DATA <line>:<col> - <line>:<col>".
 *
 * \param destination Output file.
 * \param memory      Final memory layout (MALBOLGE_MEMORY_SIZE cells).
 */
void print_source_positions(FILE *destination, MemoryCell memory[C2 + 1]);

/**
 * Writes the xlat2 cycle characters and source positions for every code cell.
 * Used by third-party debug tools that parse the .dbg file.
 *
 * \param destination Output file.
 * \param memory      Final memory layout (MALBOLGE_MEMORY_SIZE cells).
 */
void print_xlat2_positions(FILE *destination, MemoryCell memory[C2 + 1]);

#endif /* LMAO_DEBUG_H */
