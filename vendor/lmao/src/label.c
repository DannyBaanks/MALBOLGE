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

#include "label.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Suppress repeated warnings about labels pointing to unused data cells. */
static int unused_datacell_warning_shown = 0;

int insert_label(unsigned char destination_type, void *destination,
                 const char *label, LabelTree **labeltree,
                 const HeLLCodePosition *code_pos) {
	if (labeltree == NULL) {
		fprintf(stderr, "Internal error: Pointer to label tree is NULL\n");
		return 0;
	}
	if (label == NULL) {
		fprintf(stderr, "Internal error: Label is NULL\n");
		return 0;
	}
	if (destination == NULL) {
		fprintf(stderr, "Error: Label definition must be followed by a data or code word\n");
		return 0;
	}

	while (*labeltree != NULL) {
		int cmp = strncmp(label, (*labeltree)->label, 101);
		if (cmp > 0) {
			labeltree = &(*labeltree)->left;
		} else if (cmp < 0) {
			labeltree = &(*labeltree)->right;
		} else {
			char msg[140];
			if (strlen(label) <= 100)
				sprintf(msg, "Label %s is defined multiple times", label);
			else
				sprintf(msg, "Label is defined multiple times");
			fprintf(stderr, "Error: %s at line %d column %d.\n",
			        msg, code_pos->first_line, code_pos->first_column);
			return 0;
		}
	}

	*labeltree = (LabelTree *)malloc(sizeof(LabelTree));
	(*labeltree)->left = NULL;
	(*labeltree)->right = NULL;
	(*labeltree)->label = label;
	(*labeltree)->code_position = *code_pos;

	if (destination_type == 0) {
		(*labeltree)->destination_code = (CodeBlock *)destination;
		(*labeltree)->destination_data = NULL;
	} else {
		(*labeltree)->destination_code = NULL;
		(*labeltree)->destination_data = (DataBlock *)destination;
	}
	return 1;
}

int get_label(CodeBlock **destination_code, DataBlock **destination_data,
              const char *label, LabelTree *labeltree) {
	if (labeltree == NULL || label == NULL
			|| (destination_code == NULL && destination_data == NULL))
		return 0;

	while (labeltree != NULL) {
		int cmp = strncmp(label, labeltree->label, 101);
		if (cmp > 0) {
			labeltree = labeltree->left;
		} else if (cmp < 0) {
			labeltree = labeltree->right;
		} else {
			/* Found. */
			if (labeltree->destination_code != NULL
					&& labeltree->destination_data != NULL)
				return 0; /* inconsistent tree entry */

			if (labeltree->destination_code != NULL) {
				if (destination_code == NULL)
					return 0; /* caller expected data label */
				*destination_code = labeltree->destination_code;
				if (destination_data != NULL)
					*destination_data = NULL;
			} else if (labeltree->destination_data != NULL) {
				if (destination_data == NULL)
					return 0; /* caller expected code label */
				*destination_data = labeltree->destination_data;
				if (destination_code != NULL)
					*destination_code = NULL;
			} else {
				return 0; /* empty tree entry */
			}

			/* Warn once about labels that point to unused data cells. */
			if (labeltree->destination_data != NULL) {
				DataCell *cell = labeltree->destination_data->data;
				if (cell->_operator == DATACELL_OPERATOR_NOT_USED
						&& !unused_datacell_warning_shown) {
					unused_datacell_warning_shown = 1;
					fprintf(stderr,
					        "Warning: The label %s at line %d column %d points to an "
					        "unused data cell.\nLabels pointing to unused data cells "
					        "are not supported yet.\nThis may cause a crash or faulty "
					        "error messages.\nFurther warnings of this type will be "
					        "suppressed.\n",
					        label,
					        labeltree->code_position.first_line,
					        labeltree->code_position.first_column);
				}
			}

			return 1;
		}
	}
	return 0; /* not found */
}

void print_labeltree(FILE *destination, LabelTree *labeltree) {
	if (destination == NULL || labeltree == NULL)
		return;

	if (labeltree->label != NULL) {
		if (labeltree->destination_code != NULL
				&& labeltree->destination_data == NULL) {
			fprintf(destination, "%s: CODE %d\n",
			        labeltree->label,
			        labeltree->destination_code->offset);
		} else if (labeltree->destination_data != NULL
				&& labeltree->destination_code == NULL) {
			fprintf(destination, "%s: DATA %d\n",
			        labeltree->label,
			        labeltree->destination_data->offset);
		}
	}
	print_labeltree(destination, labeltree->left);
	print_labeltree(destination, labeltree->right);
}
