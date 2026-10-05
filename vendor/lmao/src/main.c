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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "types.h"
#include "globals.h"
#include "malbolge.h"
#include "xlat.h"
#include "label.h"
#include "layout.h"
#include "prefix.h"
#include "debug.h"
#include "cli.h"
#include "initialize.h"

/** Bison-generated parser entry point. */
int yyparse(void);

/**
 * Main routine: parse arguments, assemble the HeLL source, write Malbolge output.
 */
int main(int argc, char **argv) {
	int line_length = 0;
	int fast_mode = 0;
	int execution_steps_until_entry_point = -1;
	char *output_filename = NULL;
	char *debug_filename  = NULL;
	const char *input_filename = NULL;

	MemoryCell *preinitialized_section   = (MemoryCell *)malloc(MALBOLGE_MEMORY_SIZE * sizeof(MemoryCell));
	MemoryCell *to_be_initialized_section = (MemoryCell *)malloc(MALBOLGE_MEMORY_SIZE * sizeof(MemoryCell));
	MemoryCell *fixed_offsets            = (MemoryCell *)malloc(MALBOLGE_MEMORY_SIZE * sizeof(MemoryCell));
	MemoryCell *memory_layout            = (MemoryCell *)malloc(MALBOLGE_MEMORY_SIZE * sizeof(MemoryCell));

	DataBlock *entrypoint = NULL;

	unsigned int i;
	int last_preinitialized_position;
	char program[C2 + 2];
	int opcodes[C2 + 1];
	char smaller_program[MALBOLGE_MEMORY_SIZE + 1];
	int initialize_code_size = 0;
	int smaller_program_success;
	FILE *outputfile;
	HeLLCodePosition unset_position;

	printf("This is LMAO v0.6.0 (Low-level Malbolge Assembler, Ooh!) by Matthias Lutter.\n");

	if (!parse_input_args(argc, argv, &line_length, &fast_mode,
	                      &output_filename, &input_filename, &debug_filename)) {
		print_usage_message(argc > 0 ? argv[0] : NULL);
		free(preinitialized_section);
		free(to_be_initialized_section);
		free(fixed_offsets);
		free(memory_layout);
		return 0;
	}

	if (freopen(input_filename, "r", stdin) == NULL) {
		fprintf(stderr, "Error: Cannot open file %s\n", input_filename);
		return 1;
	}

	/* debug_mode is set before yyparse so the lexer can see it. */
	debug_mode = (debug_filename != NULL) ? 1 : 0;

	/* Parse the HeLL source. */
	if (yyparse()) {
		return 1;
	}

	/* Find the ENTRY label in the data section. */
	if (!get_label(NULL, &entrypoint, "ENTRY", labeltree) || entrypoint == NULL) {
		fprintf(stderr, "Error: Cannot find entry point (label ENTRY) in data section.\n");
		return 1;
	}

	/* Resolve U_ and R_ prefix references. */
	if (!handle_u_and_r_prefixes(&datablocks, &codeblocks, labeltree)) {
		return 1;
	}

	/* Initialize the three partial memory layouts to UNUSED. */
	unset_position.first_line = unset_position.first_column = -1;
	unset_position.last_line  = unset_position.last_column  = -1;
	for (i = 0; i <= C2; i++) {
		preinitialized_section[i].usage = UNUSED;
		to_be_initialized_section[i].usage = UNUSED;
		fixed_offsets[i].usage = UNUSED;
		COPY_CODE_POSITION(preinitialized_section[i].code_position,   unset_position, unset_position);
		COPY_CODE_POSITION(to_be_initialized_section[i].code_position, unset_position, unset_position);
		COPY_CODE_POSITION(fixed_offsets[i].code_position,            unset_position, unset_position);
	}

	/* Assign code blocks to one of the three partial layouts. */
	for (i = 0; i < codeblocks.size; i++) {
		CodeBlock *cur = codeblocks.codefield[i];
		unsigned char possible_positions[94];
		int needs_initialization = 0;
		int j;
		int pos = 0;

		if (cur->num_of_blocks < 1)
			continue;

		/* Set up the initial set of candidate positions (mod 94). */
		for (j = 0; j < 94; j++) {
			possible_positions[j] = (cur->offset < 0)
				? 2
				: (cur->offset % 94 == j ? 2 : 0);
		}

		/* Filter positions by each xlat2 cycle in the block. */
		while (cur != NULL) {
			int positions_left = 0;
			int preinit_positions_left = 0;
			XlatCycle *cmd = cur->command;

			for (j = 0; j < 94; j++) {
				char symbol = 0;
				if (possible_positions[j] != 0
						&& !is_xlatcycle_existent(cmd, (j + pos) % 94, &symbol))
					possible_positions[j] = 0;
				if (possible_positions[j] == 2
						&& !is_valid_initial_character((j + pos) % 94, symbol))
					possible_positions[j] = 1;
				if (possible_positions[j] != 0)
					positions_left = 1;
				if (possible_positions[j] == 2)
					preinit_positions_left = 1;
			}
			pos++;

			if (!positions_left) {
				fprintf(stderr,
				        "Error: Forced xlat cycle doesn't exist at line %d column %d.\n",
				        cur->code_position.first_line,
				        cur->code_position.first_column);
				return 1;
			}
			if (!preinit_positions_left)
				needs_initialization = 1;

			cur = cur->next;
		}

		/* If preinitialization is possible, discard the initialization-only positions. */
		if (!needs_initialization) {
			for (j = 0; j < 94; j++) {
				if (possible_positions[j] == 1)
					possible_positions[j] = 0;
			}
		}

		/* Add the block to the appropriate partial layout. */
		{
			MemoryCell *target_layout;
			if (codeblocks.codefield[i]->offset >= 0)
				target_layout = fixed_offsets;
			else if (needs_initialization)
				target_layout = to_be_initialized_section;
			else
				target_layout = preinitialized_section;

			if (!add_codeblock_to_memory_layout(codeblocks.codefield[i],
			                                    target_layout,
			                                    possible_positions,
			                                    needs_initialization)) {
				if (codeblocks.codefield[i]->offset >= 0)
					fprintf(stderr, "Error: Overlapping offsets in code section.\n");
				else
					fprintf(stderr,
					        "Error: Code section too big: Exceeds maximum size of Malbolge program.\n");
				return 1;
			}
		}
	}

	/* Assign data blocks to the appropriate partial layout. */
	for (i = 0; i < datablocks.size; i++) {
		if (datablocks.datafield[i]->num_of_blocks < 1)
			continue;
		{
			MemoryCell *target_layout = (datablocks.datafield[i]->offset >= 0)
				? fixed_offsets
				: to_be_initialized_section;
			if (!add_datablock_to_memory_layout(datablocks.datafield[i], target_layout)) {
				if (datablocks.datafield[i]->offset >= 0)
					fprintf(stderr,
					        "Error: Overlapping offsets in data section or between code and data section.\n");
				else
					fprintf(stderr,
					        "Error: Code/Data sections too big: Exceeds maximum size of Malbolge program.\n");
				return 1;
			}
		}
	}

	srand((unsigned int)time(NULL));

	/*
	 * Assemble the program. When fast mode is requested but fails due to memory
	 * conflicts, we automatically fall back to normal mode and try once more.
	 */
	{
		int retry = 1;
		while (retry) {
			retry = 0;

			/* Initial probe: use the full memory space as the upper bound to get
			 * a rough estimate of the initialization code size. */
			last_preinitialized_position = 0;
			if (!put_all_memcells_together(fixed_offsets, to_be_initialized_section,
			                               preinitialized_section, memory_layout,
			                               &last_preinitialized_position,
			                               MALBOLGE_MEMORY_SIZE, 0)) {
				fprintf(stderr,
				        "Error: Not enough memory in virtual Malbolge machine or fixed offsets in reserved area.\n");
				return 1;
			}

			update_offsets(memory_layout);
			if (generate_opcodes_from_memory_layout(memory_layout, last_preinitialized_position,
			                                        opcodes, labeltree, 1, 0) != 0) {
				initialize_code_size = generate_malbolge_initialization_code(
					opcodes, last_preinitialized_position,
					entrypoint->offset, program, 0,
					&execution_steps_until_entry_point, 0);
			} else {
				program[0] = 0;
				initialize_code_size = 0;
			}

			if (initialize_code_size > 0) {
				/* Use 2/3 of the probed size as a conservative starting estimate. */
				initialize_code_size = (initialize_code_size * 2) / 3;
			} else {
				int result = generate_opcodes_from_memory_layout(
					memory_layout, last_preinitialized_position,
					opcodes, labeltree, 0, 1);
				if (result != 0) {
					initialize_code_size = generate_malbolge_initialization_code(
						opcodes, last_preinitialized_position,
						entrypoint->offset, program, 0,
						&execution_steps_until_entry_point, 1);
					program[0] = 0;
					if (initialize_code_size <= 0)
						initialize_code_size = (C2 * 2) / 3;
				} else {
					initialize_code_size = (C2 * 2) / 3;
					program[0] = 0;
				}
			}

			/* Iteratively grow the size estimate until a valid program is produced. */
			smaller_program_success = 0;
			while (initialize_code_size < MALBOLGE_MEMORY_SIZE) {
				int j;
				execution_steps_until_entry_point = -1;
				if (fast_mode)
					initialize_code_size = MALBOLGE_MEMORY_SIZE;

				/* Reset the output layout for this attempt. */
				for (j = 0; j <= C2; j++) {
					memory_layout[j].usage = UNUSED;
					COPY_CODE_POSITION(memory_layout[j].code_position,
					                   unset_position, unset_position);
				}

				last_preinitialized_position = 0;
				if (!put_all_memcells_together(fixed_offsets, to_be_initialized_section,
				                               preinitialized_section, memory_layout,
				                               &last_preinitialized_position,
				                               initialize_code_size, 1)) {
					initialize_code_size += 32;
					continue;
				}
				update_offsets(memory_layout);
				if (!generate_opcodes_from_memory_layout(memory_layout,
				                                         last_preinitialized_position,
				                                         opcodes, labeltree, 1, 0)) {
					initialize_code_size += 32;
					continue;
				}
				if (generate_malbolge_initialization_code(
						opcodes, last_preinitialized_position,
						entrypoint->offset, smaller_program, 1,
						&execution_steps_until_entry_point, 0) < 0) {
					initialize_code_size += 32;
					continue;
				}
				smaller_program_success = 1;
				break;
			}

			if (!smaller_program_success && fast_mode) {
				fprintf(stderr,
				        "Warning: Memory usage conflict in fast mode. Retrying in normal mode...\n");
				fast_mode = 0;
				program[0] = 0;
				initialize_code_size = 0;
				retry = 1;
			}
		}
	}

	if (!smaller_program_success) {
		fprintf(stderr,
		        "Error: Memory usage conflict while generating initialization code.\n"
		        "The program may be too large, or a .OFFSET directive may conflict.\n");
		return 1;
	}

	/* Write the Malbolge output file. */
	{
		int size = 0;
		while (smaller_program[size] != 0)
			size++;

		outputfile = fopen(output_filename, "wt");
		if (outputfile == NULL) {
			fprintf(stderr, "Error: Cannot write to file %s\n", output_filename);
			return 1;
		}
		if (line_length > 0 && line_length < size) {
			int remaining = size;
			while (remaining > 0) {
				int chunk = (remaining > line_length) ? line_length : remaining;
				fwrite(smaller_program + size - remaining, 1, chunk, outputfile);
				fwrite("\n", 1, 1, outputfile);
				remaining -= line_length;
			}
		} else {
			fwrite(smaller_program, 1, size, outputfile);
			fwrite("\n", 1, 1, outputfile);
		}
		fclose(outputfile);
		printf("Malbolge code written to %s\n", output_filename);
	}

	/* Write the optional debug file. */
	if (debug_filename != NULL) {
		FILE *debugfile = fopen(debug_filename, "wt");
		if (debugfile == NULL) {
			fprintf(stderr,
			        "Error: Cannot write debugging information to file %s\n",
			        debug_filename);
			return 1;
		}
		fprintf(debugfile, ":LABELS:\n");
		print_labeltree(debugfile, labeltree);
		fprintf(debugfile, ":SOURCEPOSITIONS:\n");
		print_source_positions(debugfile, memory_layout);
		fprintf(debugfile, ":EXECUTION_STEPS_UNTIL_ENTRY_POINT:\n");
		fprintf(debugfile, "%d\n", execution_steps_until_entry_point);
		fprintf(debugfile, ":SOURCE_FILE:\n");
		fprintf(debugfile, "%s\n", input_filename);
		fprintf(debugfile, ":MALBOLGE_FILE:\n");
		fprintf(debugfile, "%s\n", output_filename);
		fprintf(debugfile, ":XLAT2:\n");
		print_xlat2_positions(debugfile, memory_layout);
		fclose(debugfile);
		printf("Debugging information written to %s\n", debug_filename);
	}

	free(preinitialized_section);
	free(to_be_initialized_section);
	free(fixed_offsets);
	free(memory_layout);
	free(output_filename);
	free(debug_filename);
	return 0;
}
