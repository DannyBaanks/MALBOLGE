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

#include "debug.h"
#include "xlat.h"
#include <stdio.h>

void print_source_positions(FILE *destination, MemoryCell memory[C2 + 1]) {
	int i;
	if (destination == NULL)
		return;

	for (i = 0; i < C2 + 1; i++) {
		if (memory[i].usage == CODE || memory[i].usage == PREINITIALIZED_CODE) {
			fprintf(destination,
			        "%d: CODE %d:%d - %d:%d\n",
			        i,
			        memory[i].code->code_position.first_line,
			        memory[i].code->code_position.first_column,
			        memory[i].code->code_position.last_line,
			        memory[i].code->code_position.last_column);
		} else if (memory[i].usage == DATA || memory[i].usage == RESERVED_DATA) {
			fprintf(destination,
			        "%d: DATA %d:%d - %d:%d\n",
			        i,
			        memory[i].data->code_position.first_line,
			        memory[i].data->code_position.first_column,
			        memory[i].data->code_position.last_line,
			        memory[i].data->code_position.last_column);
		}
	}
}

void print_xlat2_positions(FILE *destination, MemoryCell memory[C2 + 1]) {
	int i;
	if (destination == NULL)
		return;

	for (i = 0; i < C2 + 1; i++) {
		char current_char;
		XlatCycle *current_command;
		XlatCycle *tmp;
		int is_rnop;

		if (!memory[i].code
				|| (memory[i].usage != CODE && memory[i].usage != PREINITIALIZED_CODE))
			continue;
		if (memory[i].code->virtual_block)
			continue;

		current_command = memory[i].code->command;
		if (!current_command)
			continue;
		if (!is_xlatcycle_existent(current_command, i % 94, &current_char))
			continue;

		/* Check if the whole cycle is a loop-resistant NOP. */
		tmp = current_command;
		is_rnop = 1;
		do {
			if (tmp->cmd != MALBOLGE_COMMAND_NOP)
				is_rnop = 0;
			tmp = tmp->next;
		} while (tmp && tmp != current_command && is_rnop);

		if (is_rnop) {
			/* Emit one entry per character in the NOP's xlat2 orbit. */
			char first_char = current_char;
			do {
				fprintf(destination,
				        "%d %c %d:%d - %d:%d\n",
				        i,
				        current_char,
				        memory[i].code->code_position.first_line,
				        memory[i].code->code_position.first_column,
				        memory[i].code->code_position.last_line,
				        memory[i].code->code_position.last_column);
				current_char = XLAT2[(int)current_char - 33];
			} while (current_char != first_char);
			continue;
		}

		/* Emit one entry per command in the cycle. */
		while (current_command) {
			fprintf(destination,
			        "%d %c %d:%d - %d:%d\n",
			        i,
			        current_char,
			        current_command->code_position.first_line,
			        current_command->code_position.first_column,
			        current_command->code_position.last_line,
			        current_command->code_position.last_column);
			current_char = XLAT2[(int)current_char - 33];
			current_command = current_command->next;
		}
	}
}
