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

#ifndef LMAO_TYPES_H
#define LMAO_TYPES_H

#include <stddef.h> /* NULL */

/**
 * Total number of memory cells in the Malbolge virtual machine (C2 + 1 = 59049).
 */
#define MALBOLGE_MEMORY_SIZE 59049

/**
 * Copies a source code position range from two YYLTYPE-compatible structs into a HeLLCodePosition.
 * Both from_start and from_end must have first_line, first_column, last_line, last_column fields.
 */
#define COPY_CODE_POSITION(to, from_start, from_end) \
	do { \
		(to).first_line   = (from_start).first_line; \
		(to).first_column = (from_start).first_column; \
		(to).last_line    = (from_end).last_line; \
		(to).last_column  = (from_end).last_column; \
	} while (0)

/**
 * Source position of a token or expression in the HeLL source file.
 */
typedef struct HeLLCodePosition {
	int first_line;
	int first_column;
	int last_line;
	int last_column;
} HeLLCodePosition;

/**
 * Represents a single command in a Malbolge xlat2 cycle.
 * Cycles are stored as linked lists; a loop-resistant NOP links to itself.
 */
typedef struct XlatCycle {
	/** Numeric Malbolge command opcode (NOP, MOVD, OPR, JMP, ROT, OUT, IN, or HLT). */
	unsigned char cmd;
	/** Source position for error messages. */
	HeLLCodePosition code_position;
	/** Next element in the xlat2 cycle, or NULL if this is the last (non-loop-resistant) command. */
	struct XlatCycle *next;
} XlatCycle;

/**
 * Terminal node of a DataCell expression tree.
 * Represents either a numeric constant or a reference to a label.
 */
typedef struct DataAtom {
	/**
	 * Name of the label this atom references, or NULL if it is a numeric constant.
	 */
	const char *destination_label;
	/**
	 * When destination_label is NULL:
	 *   >= 0  absolute constant value
	 *   == -1 unused cell marker
	 *   == -2 don't-care marker
	 * When destination_label is non-NULL: offset added to the label address.
	 * The special value 1 encodes the R_ prefix (successor-cell offset).
	 */
	int number;
	/**
	 * Non-NULL when a U_ prefix is pending: name of the data label whose relative
	 * offset within its block must be subtracted from this cell's value.
	 * Resolved to NULL and a numeric offset by handle_u_and_r_prefixes().
	 */
	const char *operand_label;
	/** Source position for error messages. */
	HeLLCodePosition code_position;
} DataAtom;

/** DataCell is a leaf holding a DataAtom directly. */
#define DATACELL_OPERATOR_LEAF_ELEMENT 0
/** DataCell is the result of left + right. */
#define DATACELL_OPERATOR_PLUS         1
/** DataCell is the result of left - right. */
#define DATACELL_OPERATOR_MINUS        2
/** DataCell is the result of left * right. */
#define DATACELL_OPERATOR_TIMES        3
/** DataCell is the result of left / right. */
#define DATACELL_OPERATOR_DIVIDE       4
/** DataCell is the result of left >> right (tritwise rotate right). */
#define DATACELL_OPERATOR_ROTATE_R     5
/** DataCell is the result of left << right (tritwise rotate left). */
#define DATACELL_OPERATOR_ROTATE_L     6
/** DataCell is the result of crazy(left, right). */
#define DATACELL_OPERATOR_CRAZY        7
/** DataCell marks a don't-care memory cell (value unimportant, but cell reserved). */
#define DATACELL_OPERATOR_DONTCARE     8
/** DataCell marks an unused memory cell (available for reuse). */
#define DATACELL_OPERATOR_NOT_USED     9

/**
 * Expression tree node for a data section memory cell value.
 * Terminal nodes have _operator == DATACELL_OPERATOR_LEAF_ELEMENT and a non-NULL leaf_element.
 * Internal nodes have left_element and right_element set to the operand sub-trees.
 */
typedef struct DataCell {
	DataAtom *leaf_element;
	int _operator;
	struct DataCell *left_element;
	struct DataCell *right_element;
} DataCell;

/**
 * One node in a doubly-linked list of contiguous data-section memory cells.
 */
typedef struct DataBlock {
	/** Value of this memory cell, as an expression tree. */
	DataCell *data;
	/** Absolute offset in the final Malbolge program, or -1 if not yet assigned. */
	int offset;
	/** Source position for error messages. */
	HeLLCodePosition code_position;
	/** Next cell in the contiguous block, or NULL. */
	struct DataBlock *next;
	/** Previous cell in the contiguous block, or NULL. */
	struct DataBlock *prev;
	/** Number of cells from this node to the end of the block (inclusive). */
	int num_of_blocks;
} DataBlock;

/**
 * One node in a doubly-linked list of contiguous code-section memory cells.
 */
typedef struct CodeBlock {
	/** xlat2 cycle command at this position. */
	XlatCycle *command;
	/** Absolute offset in the final Malbolge program, or -1 if not yet assigned. */
	int offset;
	/** Source position for error messages. */
	HeLLCodePosition code_position;
	/** Next cell in the contiguous block, or NULL. */
	struct CodeBlock *next;
	/** Previous cell in the contiguous block, or NULL. */
	struct CodeBlock *prev;
	/** Number of cells from this node to the end of the block (inclusive). */
	int num_of_blocks;
	/**
	 * Non-zero when this block was synthesized automatically (not written in HeLL source)
	 * as a virtual NOP prefix for a U_ prefix reference.
	 */
	int virtual_block;
} CodeBlock;

/**
 * Binary search tree node for label name resolution.
 * Exactly one of destination_data and destination_code is non-NULL.
 */
typedef struct LabelTree {
	/** Non-NULL when the label names a data-section cell. */
	DataBlock *destination_data;
	/** Non-NULL when the label names a code-section cell. */
	CodeBlock *destination_code;
	/** Label name string. */
	const char *label;
	/** Source position for error messages. */
	HeLLCodePosition code_position;
	/** Left child in BST ordering (strncmp > 0). */
	struct LabelTree *left;
	/** Right child in BST ordering (strncmp < 0). */
	struct LabelTree *right;
} LabelTree;

/**
 * Resizable array of all first DataBlock pointers defined in the HeLL program.
 */
typedef struct DataBlocks {
	DataBlock **datafield;
	unsigned int size;
} DataBlocks;

/**
 * Resizable array of all first CodeBlock pointers defined in the HeLL program.
 */
typedef struct CodeBlocks {
	CodeBlock **codefield;
	unsigned int size;
} CodeBlocks;

/** Memory cell is not used in the assembled program. */
#define UNUSED              0
/**
 * Memory cell holds a code word that is embedded directly in the Malbolge source
 * (no runtime initialization needed).
 */
#define PREINITIALIZED_CODE 1
/**
 * Memory cell holds a code word that must be written at runtime by the
 * initialization code sequence.
 */
#define CODE                2
/**
 * Memory cell holds a data value that must be written at runtime by the
 * initialization code sequence.
 */
#define DATA                3
/**
 * Memory cell is reserved for the code section.
 * Its exact initial value is unimportant, but it must be in ASCII range 33-126.
 */
#define RESERVED_CODE       4
/**
 * Memory cell is reserved for the data section.
 * Its initial value is unimportant.
 */
#define RESERVED_DATA       5

/**
 * Describes the occupant and initialization mode of one Malbolge memory cell.
 */
typedef struct MemoryCell {
	/** Pointer to the CodeBlock occupying this cell, or NULL. */
	CodeBlock *code;
	/** Pointer to the DataBlock occupying this cell, or NULL. */
	DataBlock *data;
	/** One of: UNUSED, PREINITIALIZED_CODE, CODE, DATA, RESERVED_CODE, RESERVED_DATA. */
	unsigned char usage;
	/** Source position for error messages. */
	HeLLCodePosition code_position;
} MemoryCell;

#endif /* LMAO_TYPES_H */
