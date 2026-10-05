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

#include "prefix.h"
#include "label.h"
#include "malbolge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Forward declaration of recursive helper. */
static int resolve_prefixes_in_datacell(DataCell *data, DataBlock *following_block,
                                         LabelTree *labeltree);

/**
 * Resolves U_ and R_ prefix references stored in a single DataAtom.
 *
 * U_ prefix:  Calculates the relative offset of operand_label within its data
 *             block and stores it in data->number, then synthesizes virtual NOP
 *             CodeBlocks in front of the destination code label if required.
 * R_ prefix:  Validates that the destination code label has a successor cell.
 * No prefix:  Validates that the destination label exists.
 */
static int resolve_prefix_for_dataatom(DataAtom *data, DataBlock *following_block,
                                        LabelTree *labeltree) {
	if (data->destination_label == NULL)
		return 1; /* numeric constant – nothing to resolve */

	if (data->operand_label != NULL && data->number == 0) {
		/* U_ prefix: compute negative offset of operand_label from this cell. */
		DataBlock *iter = following_block;
		DataBlock *dest_data = NULL;
		CodeBlock *dest_code = NULL;
		int offset_counter = 0;

		if (!get_label(NULL, &dest_data, data->operand_label, labeltree)) {
			fprintf(stderr,
			        "Error: Cannot find label %s in data section at line %d column %d.\n",
			        data->operand_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}
		if (dest_data == NULL) {
			fprintf(stderr,
			        "Error: Internal error while looking for label %s at line %d column %d.\n",
			        data->operand_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}

		/* Walk forward in the block from following_block until we reach dest_data. */
		while (iter != NULL && iter != dest_data) {
			iter = iter->next;
			offset_counter--;
		}
		if (iter == NULL) {
			fprintf(stderr,
			        "Error: Label %s used by U_ prefixed command is not in same data "
			        "block at line %d column %d.\n",
			        data->operand_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}

		data->number = offset_counter;
		free((void *)data->operand_label);
		data->operand_label = NULL;

		/* Synthesize virtual NOP CodeBlocks before the destination code label. */
		if (!get_label(&dest_code, NULL, data->destination_label, labeltree)) {
			fprintf(stderr,
			        "Error: Cannot find label %s in code section at line %d column %d.\n",
			        data->destination_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}
		if (dest_code == NULL) {
			fprintf(stderr,
			        "Error: Internal error while looking for label %s at line %d column %d.\n",
			        data->destination_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}

		while (offset_counter < 0) {
			if (dest_code->prev != NULL) {
				/* Walk back to an existing preceding NOP. */
				XlatCycle *cycle;
				dest_code = dest_code->prev;
				cycle = dest_code->command;
				/* Walk to the last command in the cycle. */
				while (cycle->cmd == MALBOLGE_COMMAND_NOP
						&& cycle->next != NULL
						&& cycle->next != cycle)
					cycle = cycle->next;
				if (cycle->cmd != MALBOLGE_COMMAND_NOP) {
					fprintf(stderr,
					        "Error: Cannot construct nop chain for label %s at "
					        "line %d column %d.\n",
					        data->destination_label,
					        data->code_position.first_line,
					        data->code_position.first_column);
					fprintf(stderr, "Found non-nop command at line %d column %d.\n",
					        cycle->code_position.first_line,
					        cycle->code_position.first_column);
					return 0;
				}
			} else {
				/* Synthesize a new virtual NOP block in front of dest_code. */
				XlatCycle *cycle = (XlatCycle *)malloc(sizeof(XlatCycle));
				CodeBlock *code   = (CodeBlock *)malloc(sizeof(CodeBlock));
				cycle->next = cycle; /* loop-resistant NOP */
				cycle->cmd  = MALBOLGE_COMMAND_NOP;
				memcpy(&cycle->code_position, &dest_code->code_position,
				       sizeof(HeLLCodePosition));
				code->command      = cycle;
				code->prev         = NULL;
				code->next         = dest_code;
				code->virtual_block = 1;
				dest_code->prev    = code;
				code->num_of_blocks = dest_code->num_of_blocks + 1;
				code->offset       = (dest_code->offset == -1)
				                     ? -1
				                     : dest_code->offset - 1;
				memcpy(&code->code_position, &dest_code->code_position,
				       sizeof(HeLLCodePosition));
				dest_code = code;
			}
			offset_counter++;
		}

	} else if (data->operand_label == NULL && data->number == 1) {
		/* R_ prefix: verify the destination code label has a successor. */
		CodeBlock *dest = NULL;
		if (!get_label(&dest, NULL, data->destination_label, labeltree)) {
			fprintf(stderr,
			        "Error: Cannot find label %s in code block at line %d column %d.\n",
			        data->destination_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}
		if (dest == NULL) {
			fprintf(stderr,
			        "Error: Internal error while looking for label %s at "
			        "line %d column %d.\n",
			        data->destination_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}
		if (dest->next == NULL) {
			fprintf(stderr,
			        "Error: Invalid use of R_ prefix for label %s at "
			        "line %d column %d.\n",
			        data->destination_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}

	} else if (data->operand_label == NULL && data->number == 0) {
		/* Plain label reference: just check it exists. */
		CodeBlock *dest_c = NULL;
		DataBlock *dest_d = NULL;
		if (!get_label(&dest_c, &dest_d, data->destination_label, labeltree)) {
			fprintf(stderr,
			        "Error: Cannot find label %s at line %d column %d.\n",
			        data->destination_label,
			        data->code_position.first_line,
			        data->code_position.first_column);
			return 0;
		}

	} else if (data->number > 1) {
		fprintf(stderr, "Internal error.\n");
		return 0;
	}
	return 1;
}

static int resolve_prefixes_in_datacell(DataCell *data, DataBlock *following_block,
                                         LabelTree *labeltree) {
	if (data->_operator == DATACELL_OPERATOR_LEAF_ELEMENT)
		return resolve_prefix_for_dataatom(data->leaf_element, following_block, labeltree);

	if (data->left_element != NULL)
		if (!resolve_prefixes_in_datacell(data->left_element, following_block, labeltree))
			return 0;

	if (data->right_element != NULL)
		if (!resolve_prefixes_in_datacell(data->right_element, following_block, labeltree))
			return 0;

	return 1;
}

int handle_u_and_r_prefixes(DataBlocks *datablocks, CodeBlocks *codeblocks,
                              LabelTree *labeltree) {
	unsigned int i;

	if (datablocks == NULL || labeltree == NULL)
		return 0;

	/* Resolve prefixes in every data cell of every data block. */
	for (i = 0; i < datablocks->size; i++) {
		DataBlock *cur = datablocks->datafield[i];
		if (datablocks->datafield[i]->num_of_blocks < 1)
			continue;
		while (cur != NULL) {
			if (!resolve_prefixes_in_datacell(cur->data, cur->next, labeltree))
				return 0;
			cur = cur->next;
		}
	}

	/*
	 * Ensure each code-block chain in codeblocks[] starts at the true head
	 * (virtual NOP blocks may have been prepended by the U_ resolution above).
	 */
	for (i = 0; i < codeblocks->size; i++) {
		CodeBlock *cur = codeblocks->codefield[i];
		while (cur->prev != NULL)
			codeblocks->codefield[i] = (cur = cur->prev);
	}

	return 1;
}
