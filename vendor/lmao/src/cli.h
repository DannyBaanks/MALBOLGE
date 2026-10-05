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

#ifndef LMAO_CLI_H
#define LMAO_CLI_H

/**
 * Prints a usage message to stdout.
 *
 * \param executable_name  argv[0] of the program, or NULL to use "./lmao".
 */
void print_usage_message(char *executable_name);

/**
 * Parses command-line arguments for LMAO.
 *
 * Recognized options:
 *   -o <file>    Output filename.
 *   -f           Fast mode (produces larger output).
 *   -l <number>  Insert a newline every <number> characters in the output.
 *   -d           Write a .dbg debug file alongside the .mb output.
 *
 * \param argc             argc from main().
 * \param argv             argv from main().
 * \param line_length      Receives the line-length value (0 = no breaks).
 * \param fast_mode        Receives 1 if -f was given, 0 otherwise.
 * \param output_filename  Receives a newly allocated output filename string.
 * \param input_filename   Receives a pointer into argv for the input filename.
 * \param debug_filename   Receives a newly allocated debug filename string,
 *                         or NULL if -d was not given.
 * \return Non-zero on success; zero when arguments are invalid.
 */
int parse_input_args(int argc, char **argv,
                     int *line_length, int *fast_mode,
                     char **output_filename, const char **input_filename,
                     char **debug_filename);

#endif /* LMAO_CLI_H */
