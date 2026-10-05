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

#include "malbolge.h"
#include "types.h"
#include "label.h"
#include "xlat.h"
#include "gen_init.h"
#include "initialize.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void update_offsets(MemoryCell memory[]) {
	int i;
	for (i = 0; i <= C2; i++) {
		if (memory[i].usage == CODE || memory[i].usage == PREINITIALIZED_CODE)
			memory[i].code->offset = i;
		if (memory[i].usage == DATA || memory[i].usage == RESERVED_DATA)
			memory[i].data->offset = i;
	}
}

/**
 * Evaluates a leaf DataAtom to its numeric Malbolge address or value.
 *
 * For numeric atoms the stored number is returned directly (with the
 * address-decrement applied for label references, see note in the .DATA
 * section documentation).  Returns -1 on error.
 */
static int parse_dataatom(DataAtom* data, LabelTree* labeltree, int no_error_printing) {
	int value = -1;
	if (data==0)
			return -1; /* ERROR */
	if (data->destination_label == 0)
		/* data is a constant integer number. */
		value = data->number;
	else{
		/* data is an address. */
		/* get type of addressed memory cell: data or code word. */
		CodeBlock* destination_c = 0;
		/* get addressed memory cell.*/
		DataBlock* destination_d = 0;
		if (!get_label(&destination_c, &destination_d, data->destination_label, labeltree)){
			if (!no_error_printing) {
				fprintf(stderr,"Internal error: Cannot find label %s again.\n", data->destination_label);
			}
			return -1; /*ERROR! */
		}
		/* destination_type: CODE = 0; DATA = 1 */
		/* cast destination pointer according to destination_type. */
		/* add offset to destination address */
		if (destination_c != NULL) {
			value = destination_c->offset + data->number;
		}else if (destination_d != NULL) {
			value = destination_d->offset + data->number;
		}else{
			if (!no_error_printing) {
				fprintf(stderr,"Internal error: Invalid type of label %s.\n",data->destination_label);
			}
			return -1; /*ERROR! */
		}
		/* subtract one from pointer address: this is done to compensate the auto increment of C and D register in Malbolge. */
		/* handle underflow */
		if (value == 0)
			value = C2;
		else
			value--;
	}
	return value;
}

/**
 * Recursively evaluates a DataCell expression tree to a numeric value.
 *
 * Handles all arithmetic operators (PLUS, MINUS, TIMES, DIVIDE, ROTATE_R,
 * ROTATE_L, CRAZY) and leaf nodes by delegating to parse_dataatom().
 * Returns -1 on error; the result is normalized to [0, C2].
 */
static int parse_datacell(DataCell* data, LabelTree* labeltree, int no_error_printing) {
	int value = -1;
	int left = -1;
	int right = -1;
	if (data==0)
		return -1; /* ERROR */
	if (data->leaf_element != 0) {
		return parse_dataatom(data->leaf_element, labeltree, no_error_printing);
	}
	left = parse_datacell(data->left_element, labeltree, no_error_printing);
	if (left<0 || left > C2)
		return -1;
	right = parse_datacell(data->right_element, labeltree, no_error_printing);
	if (right<0 || right > C2)
		return -1;
	switch (data->_operator) {
		case DATACELL_OPERATOR_PLUS:
			value = left + right;
			break;
		case DATACELL_OPERATOR_MINUS:
			value = left - right;
			break;
		case DATACELL_OPERATOR_TIMES:
			value = left * right;
			break;
		case DATACELL_OPERATOR_DIVIDE:
			value = left / right;
			break;
		case DATACELL_OPERATOR_CRAZY:
			value = crazy(left, right);
			break;
		case DATACELL_OPERATOR_ROTATE_L:
			/* WARN IF GREATER/EQUAL 10! */
			if (right >= 10 && !no_error_printing) {
				fprintf(stderr,"Warning: Rotate left operator (<<) with right operand greater or equal 10 found.\n");
				right %= 10;
			}
			{
				int i=0;
				value = left;
				if (right == 0)
					break;
				for (i=right;i<10;i++)
					value = rotate_right(value);
			}
			break;
		case DATACELL_OPERATOR_ROTATE_R:
			/* WARN IF GREATER/EQUAL 10! */
			if (right >= 10 && !no_error_printing) {
				fprintf(stderr,"Warning: Rotate right operator (>>) with right operand greater or equal 10 found.\n");
				right %= 10;
			}
			{
				int i=0;
				value = left;
				if (right == 0)
					break;
				for (i=0;i<right;i++)
					value = rotate_right(value);
			}
			break;
		default:
			return -1; /* ERROR */
	}
	/* normalize value (may be critical for negative shift values!) */
	if (value > C2)
		value %= C2;
	while (value < 0)
		value += C2+1;
	return value;
}

int generate_opcodes_from_memory_layout(MemoryCell* memory_layout, int last_preinitialized, int* opcodes, LabelTree* labeltree, int no_error_printing, int ignore_fixed_offsets_in_preinitialized_section){
	int i;
	int last_opcode_from_33_to_126 = 81; /* store it to find best value for reserved code word */
	for (i=0;i<=C2;i++){
		opcodes[i] = -1;
		if (memory_layout[i].usage == CODE || memory_layout[i].usage == PREINITIALIZED_CODE) {
			char symbol;
			if (!is_xlatcycle_existent(memory_layout[i].code->command, i%94, &symbol)){
				if (!no_error_printing)
					fprintf(stderr,"Internal error: Cannot find xlat2 cycle again.\n");
				return 0; /*ERROR! */
			}
			opcodes[i] = (unsigned char)symbol;
			if (i > last_preinitialized) {
				last_opcode_from_33_to_126 = opcodes[i];
			}
			if (i <= last_preinitialized && !is_valid_initial_character(i%94, symbol) && !ignore_fixed_offsets_in_preinitialized_section) {
				if (!no_error_printing)
					fprintf(stderr,"Error: Invalid symbol in preinitialized code section.\n");
				return 0; /* ERROR! */
			}
		}else if (memory_layout[i].usage == DATA) {
			int data = parse_datacell(memory_layout[i].data->data, labeltree, no_error_printing);
			if (data < 0){
					if (!no_error_printing)
						fprintf(stderr,"Internal error: Found negative value in data segment.\n");
					return 0; /*ERROR! */
			}
			opcodes[i] = data;
			if (opcodes[i] < 127 && opcodes[i] > 32) {
				last_opcode_from_33_to_126 = opcodes[i];
			}
			if (i <= last_preinitialized && !ignore_fixed_offsets_in_preinitialized_section) {
				if (!no_error_printing)
					fprintf(stderr, "Error: Invalid offset in data section.\n");
				return 0; /*ERROR! */
			}
		}else if (memory_layout[i].usage == RESERVED_CODE) {
			if (i > last_preinitialized) {
				opcodes[i] = (((i%2)==(last_preinitialized%2))?81:last_opcode_from_33_to_126);
			}
		}
	}
	return 1;
}


/*
 * Constants describing the initial state of the constant-generation data
 * module directly after the init_datamodule prefix has been executed.
 * These values are tightly coupled to the init_datamodule byte string and
 * must not be changed independently of it.
 */
#define INIT_A_REG       58328  /**< A register value after init_datamodule runs. */
#define INIT_MODULE      0      /**< D register module index after init_datamodule. */
#define INIT_POS_IN_MOD  8      /**< D register position within that module. */
#define INIT_DEST_VAL    68     /**< Initial value of the DESTINATION cell. */
#define INIT_TMP_VAL     C1     /**< Initial value of the TMP cell. */
#define INIT_VAL1        126    /**< Initial value of module 1's variable cell. */
#define INIT_VAL2        58688  /**< Initial value of module 2's variable cell. */
#define INIT_VAL3        29495  /**< Initial value of module 3's variable cell. */

/** Shorthand for an unset (unused) module cell initializer. */
#define UNSET_MODULE_CELL {CELLTYPE_CONST, 0, {0, 0}}

int generate_malbolge_initialization_code(int program[], int last_preinitialized, int entrypoint, char malbolge_code[], int no_error_printing, int* execution_steps_until_entry_point, int ignore_wrong_size) {

	int i = 0;
	int size_left = 59049;
	char normalized_code_array[59050];
	char* normalized_code_iterator = 0;
	int size = 0;
	int init_datamodule_length;

	/* Malbolge code that initializes the constant generation data module. */
	const char* init_datamodule = "bP" /* Jmp; Destination for MovD */
			"&A@?>=<;:9876543210/.-,+*)('&%$T\"!~}|;]yxwvutslUSRQ.y"
			"x+i)J9edFb4`_^]\\yxwRQ)(TSRQ]m!G0KJIyxFvDa%_@?\"=<5:98"
			"765.-2+*/.-,+*)('&%$#\"!~}|utyrqvutsrqjonmPkjihgfedc\\"
			"DDYAA\\>>Y;;V886L5322G//D,,G))>&&A##!7~5:{y7xvuu,10/.-"
			",+*)('&%$#\"yb}|{zyxwvutmVqSohmOOjihafeHcEa`YAA\\[ZYRW"
			":U7SLKP3NMLK-I,GFED&%%@?>=6;|9y70/4u210/o-n+k)\"!gg$#\""
			"!x}`{zyxZvYtsrqSoRmlkjLhKfedcEaD_^]\\>Z=XWVU7S6QPON0LK"
			"DI,GFEDCBA#?\"=};438y6543s1r/o-&%*k('&%e#d!~}|^z]xwvuW"
			"sVqponPlOjihgIeHcba`B^A\\[ZY;W:UTSR4PI2MLKJ,,AFE(&B;:?"
			"\"~<}{zz165v3s+*/pn,mk)jh&ge#db~a_{^\\xwvoXsrqpRnmfkjM"
			"Kg`_GG\\aDB^A?[><X;9U86R53ONM0KJC,+FEDC&A@?!!6||3876w4"
			"-tr*/.-&+*)('&%$e\"!~}|utyxwvutWlkponmlOjchg`edGba`_XW"
			"\\?ZYRQVOT7RQPINML/JIHAFEDC&A@?>!<;{98yw5.-ss*/pn,+lj("
			"!~ff{\"ca}`^z][wZXtWUqTRnQOkNLhgfIdcFaZ_^A\\[Z<XW:U8SR"
			"QPOHML/JIHG*ED=%%:?>=~;:{876w43210/(-,+*)('h%$d\"ca}|_"
			"z\\rqYYnsVTpoRPledLLafIGcbE`BXW??TY<:V97S64P31M0.J-+G*"
			"(DCB%@?\"=<;|98765.3210p.-n+$)i'h%${\"!~}|{zyxwvuXVlkp"
			"SQmlOjLbafIGcbE`BXW??TY<:V97S64P31M0.J-+G*(D'%A@?\"=<}"
			":98y6543,1r/.o,+*)j'&%eez!~a|^tsx[YutWUqjinQOkjMhJ`_dG"
			"EaDB^A?[><X;9U86R53O20LKJ-HG*ED'BA@?>7~;:{y7x5.3210q.-"
			"n+*)jh&%$#\"c~}`{z]rwvutWrkpohmPkjihafI^cba`_^A\\[>YXW"
			":UTS5QP3NM0KJ-HGF?D'BA:?>=~;:z8765v32s0/.-nl$#(ig%fd\""
			"ca}|_]yrqvYWsVTpSQmPNjMKgJHdGEa`_B]\\?ZY<WVUTMR5PO20LK"
			".IHA))>CB%#?87}}49zx6wu3tr0qo-nl*ki'hf$ec!~}`{^yxwvots"
			"rUponQlkMihKIe^]EEZ_B@\\?=Y<:V97S64P31M0.J-+GFE(C&A@?8"
			"=<;:{876w43s10qo-&%kk\"'hf$ec!b`|_]y\\ZvYWsVTpSQmlkNiL"
			"gf_dcba`C^]\\?ZY;WV97SLK33HM0.J-+G*(D'%A$\">!};|z8yw54"
			"3t1r/(";

	/*
	 * Virtual machine state immediately after the init_datamodule prefix has
	 * been executed.  This matches the layout described in datamodule.txt:
	 *
	 *   Module 0 (offset 82): coordinator module with 15 cells
	 *   Modules 1-3 (offsets 33-40, 48-55, 71-78): value-generation modules
	 *
	 * The State struct tracks all cells that the initialization code may read
	 * or modify so that the code generator can reason about register values.
	 */
	State cur_state = {
		INIT_A_REG,
		{INIT_MODULE, INIT_POS_IN_MOD},
		{
			/* Module 0: coordinator (15 cells at offset 82-96) */
			{15, {
				{CELLTYPE_CONST, C0,  {0, 0}},
				{CELLTYPE_PTR,   0,   {0, 12}},
				{CELLTYPE_PTR,   0,   {1, 1}},
				{CELLTYPE_PTR,   0,   {2, 1}},
				{CELLTYPE_PTR,   0,   {3, 1}},
				{CELLTYPE_CONST, C1,  {0, 0}},
				{CELLTYPE_VAR,   INIT_TMP_VAL,                          {0, 0}},
				{CELLTYPE_VAR,   C2 - 2*9 - 2*9*3 - 2*9*9 - 2*9*9*3,   {0, 0}},
				{CELLTYPE_VAR,   C2 - 2*9 - 2*9*3 - 2*9*9,              {0, 0}},
				{CELLTYPE_VAR,   C2 - 2*9 - 2*9*3,                      {0, 0}},
				{CELLTYPE_VAR,   C2 - 2*9,                              {0, 0}},
				{CELLTYPE_CONST, C2,  {0, 0}},
				{CELLTYPE_VAR,   INIT_DEST_VAL,                         {0, 0}},
				{CELLTYPE_PTR,   0,   {0, 6}},
				{CELLTYPE_PTR,   0,   {0, 0}}
			}},
			/* Module 1: value generator (8 cells at offset 33-40) */
			{8, {
				{CELLTYPE_CONST,      C0,   {0, 0}},
				{CELLTYPE_CONST,      C1,   {0, 0}},
				{CELLTYPE_C20_OR_C21, C21,  {0, 0}},
				{CELLTYPE_VAR,        INIT_VAL1, {0, 0}},
				{CELLTYPE_CONST,      C2,   {0, 0}},
				{CELLTYPE_PTR,        0,    {1, 3}},
				{CELLTYPE_PTR,        0,    {1, 0}},
				{CELLTYPE_PTR,        0,    {0, 12}},
				UNSET_MODULE_CELL, UNSET_MODULE_CELL, UNSET_MODULE_CELL,
				UNSET_MODULE_CELL, UNSET_MODULE_CELL, UNSET_MODULE_CELL,
				UNSET_MODULE_CELL
			}},
			/* Module 2: value generator (8 cells at offset 48-55) */
			{8, {
				{CELLTYPE_CONST,      C0,   {0, 0}},
				{CELLTYPE_CONST,      C1,   {0, 0}},
				{CELLTYPE_C20_OR_C21, C21,  {0, 0}},
				{CELLTYPE_VAR,        INIT_VAL2, {0, 0}},
				{CELLTYPE_CONST,      C2,   {0, 0}},
				{CELLTYPE_PTR,        0,    {2, 3}},
				{CELLTYPE_PTR,        0,    {2, 0}},
				{CELLTYPE_PTR,        0,    {0, 12}},
				UNSET_MODULE_CELL, UNSET_MODULE_CELL, UNSET_MODULE_CELL,
				UNSET_MODULE_CELL, UNSET_MODULE_CELL, UNSET_MODULE_CELL,
				UNSET_MODULE_CELL
			}},
			/* Module 3: value generator (8 cells at offset 71-78) */
			{8, {
				{CELLTYPE_CONST,      C0,   {0, 0}},
				{CELLTYPE_CONST,      C1,   {0, 0}},
				{CELLTYPE_C20_OR_C21, C21,  {0, 0}},
				{CELLTYPE_VAR,        INIT_VAL3, {0, 0}},
				{CELLTYPE_CONST,      C2,   {0, 0}},
				{CELLTYPE_PTR,        0,    {3, 3}},
				{CELLTYPE_PTR,        0,    {3, 0}},
				{CELLTYPE_PTR,        0,    {0, 12}},
				UNSET_MODULE_CELL, UNSET_MODULE_CELL, UNSET_MODULE_CELL,
				UNSET_MODULE_CELL, UNSET_MODULE_CELL, UNSET_MODULE_CELL,
				UNSET_MODULE_CELL
			}}
		},
		0 /* last_preinitialized — filled in below */
	};

	cur_state.last_preinitialized = last_preinitialized;

	init_datamodule_length = (int)strlen(init_datamodule);

	/* Prepend the data-module initialization prefix to the output buffer. */
	memcpy(normalized_code_array, init_datamodule, init_datamodule_length);

	size_left = 59049 - init_datamodule_length;
	normalized_code_iterator = normalized_code_array + init_datamodule_length;

	/* Generate normalized initialization code for every cell that needs a
	 * runtime-written value (cells after last_preinitialized). */
	for (i = last_preinitialized + 1; i <= C2; i++) {
		if (program[i] >= 0) {
			size = generate_normalized_init_code_for_word_with_module_system(
				i, program[i], normalized_code_iterator,
				&cur_state, size_left, no_error_printing);
			if (size < 0) {
				if (!no_error_printing)
					fprintf(stderr, "Internal error: Cannot generate initialization code for cell %d.\n", i);
				return -1;
			}
			size_left -= size;
			normalized_code_iterator += size;
		}
	}

	/* Append the jump to the program entry point. */
	size = generate_jump_to_entrypoint_with_module_system(
		entrypoint, normalized_code_iterator, &cur_state, size_left, no_error_printing);
	if (size < 0) {
		if (!no_error_printing)
			fprintf(stderr, "Internal error: Cannot generate jump to entry point %d.\n", entrypoint);
		return -1;
	}
	size_left -= size;
	normalized_code_iterator += size;
	*normalized_code_iterator = 0;

	if (size_left < 0) {
		if (!no_error_printing)
			fprintf(stderr, "Error: Initialization code exceeds available memory.\n");
		return -1;
	}

	/*
	 * Place the 'i' (In) instruction that hands control from the initialization
	 * sequence to the HeLL program's entry point.  The constant 98 accounts for
	 * the 2 cells of the initial "bP" jump plus the 96-cell data module that
	 * Malbolge has already executed past.
	 */
	normalized_code_array[59049 - size_left] = 'i';
	if (execution_steps_until_entry_point != NULL)
		*execution_steps_until_entry_point = (59049 - size_left) - 98;
	size_left--;

	if (59049 - size_left > last_preinitialized - 1)
		return -1; /* initialization code overflows the pre-initialized region */

	/* Fill the gap between the 'i' instruction and the RQ terminator with
	 * random NOP-class opcodes so the Malbolge interpreter does not treat
	 * padding bytes as active instructions. */
	{
		static const char nop_opcodes[] = "i</*jpov";
		for (i = 59049 - size_left; i < last_preinitialized - 1; i++)
			normalized_code_array[i] = nop_opcodes[rand() % 8];
	}

	/* Verify that no user cell overlaps with the initialization code
	 * (cells 2 through end of generated init code). */
	for (i = 2; i < 59049 - size_left; i++) {
		if (program[i] >= 0) {
			if (!no_error_printing)
				fprintf(stderr, "Error: HeLL program overlaps with generated initialization code.\n");
			return -1;
		}
	}

	/* Verify that no user cell occupies the RQ terminator positions. */
	for (i = last_preinitialized - 1; i <= last_preinitialized; i++) {
		if (program[i] >= 0) {
			if (!no_error_printing)
				fprintf(stderr, "Error: HeLL program overlaps with generated initialization code.\n");
			return -1;
		}
	}

	/* Convert normalized opcodes to address-dependent Malbolge characters. */
	if (!denormalize_malbolge(
			&normalized_code_array[init_datamodule_length],
			init_datamodule_length,
			last_preinitialized - 1 - init_datamodule_length,
			no_error_printing)) {
		if (!no_error_printing)
			fprintf(stderr, "Internal error: Denormalization of initialization code failed.\n");
		return -1;
	}

	/* Write the "RQ" sequence that terminates the pre-initialized region. */
	normalized_code_array[last_preinitialized - 1] = 'R';
	normalized_code_array[last_preinitialized]     = 'Q';
	normalized_code_array[last_preinitialized + 1] = 0;

	/* Cells 0-1 must contain "bP" (the initial Jmp).  Reject conflicting
	 * user-specified values at those positions. */
	for (i = 0; i < 2; i++) {
		if (program[i] >= 0
				&& is_valid_initial_character(i % 94, program[i])
				&& program[i] != normalized_code_array[i]) {
			if (!no_error_printing)
				fprintf(stderr, "Error: HeLL program conflicts with required 'bP' at cells 0-1.\n");
			return -1;
		}
	}

	/* Allow pre-initialized code cells to replace NOP filler in the padding
	 * area between the 'i' instruction and the RQ terminator. */
	if (!ignore_wrong_size) {
		for (i = 59049 - size_left; i < last_preinitialized - 1; i++) {
			if (program[i] >= 0 && is_valid_initial_character(i % 94, program[i]))
				normalized_code_array[i] = program[i];
			else if (program[i] >= 0) {
				if (!no_error_printing)
					fprintf(stderr, "Internal error: Cannot place opcode %d at position %d.\n",
					        program[i], i);
				return -1;
			}
		}
	}

	memcpy(malbolge_code, normalized_code_array, last_preinitialized + 2);

	return 59049 - size_left; /* return offset of end of initialization code */
}


