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

/**
 * \file gen_init.h
 * \brief Constant-generation code for the Malbolge initialization sequence.
 *
 * LMAO produces a Malbolge program that consists of two parts:
 *
 *   1. An initialization sequence that writes every HeLL data and code cell to
 *      its required value before the HeLL program begins execution.
 *   2. The HeLL program itself, embedded verbatim after the initialization
 *      sequence.
 *
 * The initialization sequence is driven by a \em data \em module — a compact
 * block of memory that provides a set of known reference values (C0, C1, C2,
 * C21, and several variable cells) together with the infrastructure needed to
 * load arbitrary values into the A register and to write them to arbitrary
 * memory locations via the Malbolge Opr (crazy) and Rot (rotate) instructions.
 *
 * The State struct tracks the virtual Malbolge machine's state throughout code
 * generation so that the generator can reason about register values without
 * actually running the Malbolge interpreter.
 */

#ifndef LMAO_GEN_INIT_H
#define LMAO_GEN_INIT_H

/**
 * Identifies the location of the D register within the data module system.
 *
 * The D register either points somewhere inside one of the four data modules
 * (module 0-3, indexed by \c module), or to an absolute memory address
 * (module -1, absolute address in \c pos).
 */
typedef struct DRegPos {
	/**
	 * Module index (0-3) when the D register is inside a data module.
	 * -1 when \c pos is an absolute Malbolge memory address.
	 */
	int module;
	/**
	 * Position within the module (0-based cell index) when module >= 0.
	 * Absolute Malbolge memory address when module == -1.
	 */
	int pos;
} DRegPos;

/** Cell type: a pointer to another cell in the data module system. */
#define CELLTYPE_PTR         0

/** Cell type: a constant that the initialization code must not overwrite. */
#define CELLTYPE_CONST       1

/** Cell type: a variable that the initialization code may modify freely. */
#define CELLTYPE_VAR         2

/**
 * Cell type: a cell that holds either C20 (59046) or C21 (59047) and may only
 * be crazied with A = C0 or A = C1 (operations that preserve C20/C21).
 */
#define CELLTYPE_C20_OR_C21  3

/**
 * Represents one memory cell inside a data module.
 */
typedef struct Cell {
	/** Cell type: one of CELLTYPE_PTR, CELLTYPE_CONST, CELLTYPE_VAR,
	 *  or CELLTYPE_C20_OR_C21. */
	int type;
	/** Current value of the cell.  Valid only when type != CELLTYPE_PTR. */
	int value;
	/** Destination pointer.  Valid only when type == CELLTYPE_PTR. */
	DRegPos destination;
} Cell;

/** Maximum number of cells per data module. */
#define MODULE_MAX_CELLS 15

/**
 * One data module: a fixed-size block of memory cells used by the
 * initialization code to generate arbitrary constant values.
 *
 * Each module contains between 8 and 15 cells.  Module 0 is the coordinator;
 * modules 1-3 are value-generation modules (see datamodule.txt).
 */
typedef struct Module {
	/** Number of active cells in this module (at most MODULE_MAX_CELLS). */
	int num_of_cells;
	/** Cell values; only the first num_of_cells entries are meaningful. */
	Cell cells[MODULE_MAX_CELLS];
} Module;

/** Number of data modules in the constant-generation system. */
#define NUM_MODULES 4

/**
 * Snapshot of the Malbolge virtual machine state during execution of the
 * initialization sequence.
 *
 * The code generator maintains this state to predict the effect of each
 * generated instruction without running the full Malbolge interpreter.
 * Only cells that belong to the data module system are tracked; the values
 * of all other cells are either known constants or irrelevant.
 */
typedef struct State {
	/** Current value of the A (accumulator) register. */
	int a_reg;
	/** Current position the D (data pointer) register points to. */
	DRegPos d_reg;
	/**
	 * State of all data module cells.
	 * modules[0] is the coordinator; modules[1-3] are value generators.
	 */
	Module modules[NUM_MODULES];
	/**
	 * Address of the last pre-initialized cell in the final Malbolge program.
	 * Memory cells with addresses above this value are assumed to hold 81 or
	 * (C1 - 81) depending on their distance from this address.
	 */
	int last_preinitialized;
} State;

/**
 * Converts a buffer of normalized Malbolge opcodes to the address-dependent
 * encoding required by a real Malbolge interpreter.
 *
 * Normalized opcodes use single ASCII characters to represent each Malbolge
 * command regardless of memory position:
 *   'o' = MovD,  'j' = Jmp,  'p' = Opr,  '*' = Rot,
 *   'i' = In,    '<' = Out,  '/' = Hlt,  'v' = Nop
 *
 * The denormalized form encodes the command as
 *   (char - 33 + position) % 94 + 33
 * so that (char + position) % 94 equals the opcode the interpreter expects.
 *
 * \param normalized_code         Buffer of normalized opcodes to convert in
 *                                place.  Must contain only: o j p * i < / v
 * \param normalized_code_offset  Absolute address of the first byte in the
 *                                buffer within the Malbolge program.
 * \param code_len                Number of bytes to convert.
 * \param no_error_printing       If non-zero, suppress error output.
 * \return Non-zero on success; zero if an unrecognized opcode is encountered.
 */
int denormalize_malbolge(char *normalized_code, int normalized_code_offset,
                         int code_len, int no_error_printing);

/**
 * Generates normalized Malbolge initialization code that writes a single
 * memory cell to a target value.
 *
 * The generated code uses the data module system to load the target value into
 * the A register and then writes it to \p init_position via an Opr (crazy)
 * instruction.  The \p current_state is updated to reflect the new module cell
 * values and register state after the generated code executes.
 *
 * The caller must ensure that all cells at addresses > last_preinitialized
 * that are not inside the data module contain either 81 or (C1-81), depending
 * on whether their address is even or odd relative to \c last_preinitialized.
 *
 * \param init_position       Address of the cell to initialize.
 * \param init_value          Target value for that cell.
 * \param normalized_init_code  Output buffer for the generated normalized code.
 * \param current_state       Machine state before the generated code executes;
 *                            updated in place to the state after execution.
 * \param max_init_code_length  Size of the output buffer.
 * \param no_error_printing   If non-zero, suppress error output.
 * \return Number of bytes written to \p normalized_init_code, or -1 on error.
 */
int generate_normalized_init_code_for_word_with_module_system(
	int init_position,
	int init_value,
	char *normalized_init_code,
	State *current_state,
	int max_init_code_length,
	int no_error_printing);

/**
 * Generates normalized Malbolge code that performs a Jmp to the HeLL
 * program's entry point, concluding the initialization sequence.
 *
 * \param entry_point           Malbolge address of the ENTRY label.
 * \param normalized_init_code  Output buffer for the generated code.
 * \param current_state         Machine state before this code executes;
 *                              updated in place.
 * \param max_init_code_length  Size of the output buffer.
 * \param no_error_printing     If non-zero, suppress error output.
 * \return Number of bytes written, or -1 on error.
 */
int generate_jump_to_entrypoint_with_module_system(
	int entry_point,
	char *normalized_init_code,
	State *current_state,
	int max_init_code_length,
	int no_error_printing);

#endif /* LMAO_GEN_INIT_H */
