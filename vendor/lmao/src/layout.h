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

#ifndef LMAO_LAYOUT_H
#define LMAO_LAYOUT_H

#include "types.h"

/**
 * Places a code block into a relative memory layout array.
 *
 * The function finds the lowest unused starting position that satisfies
 * the xlat2-cycle position constraints encoded in possible_positions_mod_94.
 * A RESERVED_CODE cell is inserted immediately before the first command cell.
 *
 * \param block                    First CodeBlock in the chain to place.
 * \param memory_layout            Memory layout array (size MALBOLGE_MEMORY_SIZE).
 * \param possible_positions_mod_94 Array of 94 bytes; non-zero entries mark valid
 *                                  start positions modulo 94.
 *                                  Value 2: preinitialized is allowed.
 *                                  Value 1: needs runtime initialization.
 * \param must_be_initialized      If non-zero the cells are marked CODE;
 *                                 otherwise PREINITIALIZED_CODE.
 * \return Non-zero on success; zero when no valid position was found.
 */
int add_codeblock_to_memory_layout(CodeBlock *block,
                                   MemoryCell memory_layout[],
                                   unsigned char possible_positions_mod_94[],
                                   int must_be_initialized);

/**
 * Places a data block into a relative memory layout array.
 *
 * \param block        First DataBlock in the chain to place.
 * \param memory_layout Memory layout array (size MALBOLGE_MEMORY_SIZE).
 * \return Non-zero on success; zero when no valid position was found.
 */
int add_datablock_to_memory_layout(DataBlock *block, MemoryCell memory_layout[]);

/**
 * Merges the three partial memory layouts into a single final layout.
 *
 * Blocks with fixed offsets are taken as-is from fixedoffset.
 * Blocks requiring runtime initialization (toinitial) are aligned to a
 * modulo-94 boundary near the end of available memory.
 * Pre-initialized blocks (preinitial) are placed just before the RQ terminator.
 *
 * \param fixedoffset                Blocks with explicit .OFFSET directives.
 * \param toinitial                  Blocks needing runtime initialization.
 * \param preinitial                 Blocks that can be placed directly in source.
 * \param memory_layout              Output: the merged final layout.
 * \param last_preinitialized_cell   Output: offset of the last preinitialized cell.
 * \param end_of_initialization_code Upper bound on the initialization code length.
 *                                   Pass MALBOLGE_MEMORY_SIZE or higher to maximize
 *                                   available space (large but safe output).
 * \param no_error_printing          If non-zero, suppress error messages.
 * \return Non-zero on success; zero on failure.
 */
int put_all_memcells_together(MemoryCell fixedoffset[],
                              MemoryCell toinitial[],
                              MemoryCell preinitial[],
                              MemoryCell memory_layout[],
                              int *last_preinitialized_cell,
                              int end_of_initialization_code,
                              int no_error_printing);

#endif /* LMAO_LAYOUT_H */
