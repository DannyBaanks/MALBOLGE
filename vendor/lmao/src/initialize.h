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

#ifndef LMAO_INITIALIZE_H
#define LMAO_INITIALIZE_H

#include "types.h"

/**
 * Writes back the resolved memory address from each MemoryCell into the
 * CodeBlock or DataBlock it references.
 *
 * After the final memory layout has been assembled, every used cell has a
 * definite address.  This function propagates those addresses into the block
 * structures so that label references evaluated later will see correct values.
 *
 * \param memory  Final memory layout (exactly MALBOLGE_MEMORY_SIZE cells).
 */
void update_offsets(MemoryCell memory[]);

/**
 * Computes the Malbolge opcode for every used cell in the final memory layout.
 *
 * For CODE and PREINITIALIZED_CODE cells the opcode is derived from the xlat2
 * cycle and the cell's address.  For DATA cells the expression tree is
 * evaluated to a numeric value.  RESERVED_CODE cells are given a safe NOP-like
 * value.  UNUSED and RESERVED_DATA cells produce opcode -1.
 *
 * \param memory_layout         Final layout array (MALBOLGE_MEMORY_SIZE cells).
 * \param last_preinitialized   Address of the last cell that is part of the
 *                              pre-initialized (source-embedded) region.
 * \param opcodes               Output array (MALBOLGE_MEMORY_SIZE entries).
 *                              Each entry is the opcode for that address, or -1
 *                              if the cell is unused.
 * \param labeltree             Label BST used to resolve label references in
 *                              DATA expressions.
 * \param no_error_printing     If non-zero, error messages are suppressed.
 * \param ignore_fixed_offsets_in_preinitialized_section
 *                              If non-zero, DATA and invalid CODE cells in the
 *                              pre-initialized region are silently ignored
 *                              instead of causing an error.
 * \return Non-zero on success; zero on error.
 */
int generate_opcodes_from_memory_layout(MemoryCell *memory_layout,
                                        int last_preinitialized,
                                        int *opcodes,
                                        LabelTree *labeltree,
                                        int no_error_printing,
                                        int ignore_fixed_offsets_in_preinitialized_section);

/**
 * Generates the complete Malbolge source string for a HeLL program.
 *
 * The output consists of:
 *   1. A fixed data-module prefix (init_datamodule) that sets up the
 *      constant-generation infrastructure.
 *   2. Generated initialization code that writes every runtime-initialized
 *      cell to its target value using the data-module system.
 *   3. A jump to the HeLL program's entry point.
 *   4. NOP filler up to the RQ terminator.
 *   5. Pre-initialized code/data cells embedded directly in the source
 *      (positions > last_preinitialized).
 *   6. The "RQ" terminator that ends the pre-initialized region.
 *
 * \param program               Opcode array produced by
 *                              generate_opcodes_from_memory_layout().
 * \param last_preinitialized   Address of the last pre-initialized cell
 *                              (the "RQ" terminator is placed here).
 * \param entrypoint            Malbolge address of the HeLL program's ENTRY
 *                              label; the initialization code jumps here.
 * \param malbolge_code         Output buffer; must be at least
 *                              (last_preinitialized + 2) bytes.
 * \param no_error_printing     If non-zero, suppress error output.
 * \param execution_steps_until_entry_point
 *                              If non-NULL, receives the number of
 *                              initialization steps executed before control
 *                              reaches the entry point.
 * \param ignore_wrong_size     If non-zero, skip the final overlap check that
 *                              detects when the initialization code would
 *                              overwrite user cells.
 * \return The offset of the end of the initialization code on success;
 *         -1 on error.
 */
int generate_malbolge_initialization_code(int program[],
                                          int last_preinitialized,
                                          int entrypoint,
                                          char malbolge_code[],
                                          int no_error_printing,
                                          int *execution_steps_until_entry_point,
                                          int ignore_wrong_size);

#endif /* LMAO_INITIALIZE_H */
