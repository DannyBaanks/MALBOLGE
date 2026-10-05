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

#include "cli.h"
#include "malbolge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MALBOLGE_FILE_EXTENSION "mb"
#define DEBUG_FILE_EXTENSION    "dbg"

void print_usage_message(char *executable_name) {
	printf("Usage: %s [options] file\n",
	       executable_name != NULL ? executable_name : "./lmao");
	printf("Options:\n");
	printf("  -o <file>           Write the output into <file>\n");
	printf("  -f                  Fast mode (bigger output)\n");
	printf("  -l <number>         Insert a line break every <number> characters\n");
	printf("  -d                  Write debug information\n");
}

int parse_input_args(int argc, char **argv,
                     int *line_length, int *fast_mode,
                     char **output_filename, const char **input_filename,
                     char **debug_filename) {
	int i;
	int want_debug = 0;

	if (argc < 2 || argv == NULL || line_length == NULL || fast_mode == NULL
			|| output_filename == NULL || input_filename == NULL
			|| debug_filename == NULL)
		return 0;

	*line_length = -1;
	*output_filename = NULL;
	*input_filename = NULL;
	*fast_mode = 0;
	*debug_filename = NULL;

	for (i = 1; i < argc; i++) {
		if (argv[i][0] == '-') {
			switch (argv[i][1]) {
			case 'l': {
				long int tmp;
				i++;
				if (*line_length != -1)
					return 0; /* duplicate -l */
				if (i >= argc)
					return 0; /* missing argument */
				tmp = strtol(argv[i], NULL, 10);
				if (tmp > C2 + 1)
					tmp = C2 + 1;
				if (tmp < 0)
					tmp = 0;
				*line_length = (int)tmp;
				break;
			}
			case 'o':
				i++;
				if (*output_filename != NULL)
					return 0; /* duplicate -o */
				if (i >= argc)
					return 0; /* missing argument */
				*output_filename = (char *)malloc(strlen(argv[i]) + 1);
				memcpy(*output_filename, argv[i], strlen(argv[i]) + 1);
				break;
			case 'f':
				if (*fast_mode != 0)
					return 0; /* duplicate -f */
				*fast_mode = 1;
				break;
			case 'd':
				if (want_debug != 0)
					return 0; /* duplicate -d */
				want_debug = 1;
				break;
			default:
				return 0; /* unknown option */
			}
		} else {
			if (*input_filename != NULL)
				return 0; /* more than one input file */
			*input_filename = argv[i];
		}
	}

	if (*input_filename == NULL)
		return 0;

	if (*line_length == -1)
		*line_length = 0;

	/* Build output filename if not given explicitly. */
	if (*output_filename == NULL) {
		const char *ext = strrchr(*input_filename, '.');
		size_t base_len;
		/* Ignore the extension if it is after a path separator. */
		if (ext == NULL
				|| strrchr(*input_filename, '\\') > ext
				|| strrchr(*input_filename, '/') > ext
				|| strcmp(ext + 1, MALBOLGE_FILE_EXTENSION) == 0) {
			base_len = strlen(*input_filename);
		} else {
			base_len = (size_t)(ext - *input_filename);
		}
		*output_filename = (char *)malloc(base_len + 1 + strlen(MALBOLGE_FILE_EXTENSION) + 1);
		memcpy(*output_filename, *input_filename, base_len);
		(*output_filename)[base_len] = '.';
		memcpy(*output_filename + base_len + 1,
		       MALBOLGE_FILE_EXTENSION,
		       strlen(MALBOLGE_FILE_EXTENSION) + 1);
	}

	/* Build debug filename when -d was requested. */
	if (want_debug) {
		const char *ext = strrchr(*output_filename, '.');
		size_t base_len;
		if (ext == NULL
				|| strrchr(*output_filename, '\\') > ext
				|| strrchr(*output_filename, '/') > ext
				|| strcmp(ext + 1, DEBUG_FILE_EXTENSION) == 0) {
			base_len = strlen(*output_filename);
		} else {
			base_len = (size_t)(ext - *output_filename);
		}
		*debug_filename = (char *)malloc(base_len + 1 + strlen(DEBUG_FILE_EXTENSION) + 1);
		memcpy(*debug_filename, *output_filename, base_len);
		(*debug_filename)[base_len] = '.';
		memcpy(*debug_filename + base_len + 1,
		       DEBUG_FILE_EXTENSION,
		       strlen(DEBUG_FILE_EXTENSION) + 1);
	}

	return 1;
}
