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

#ifndef LMAO_GLOBALS_H
#define LMAO_GLOBALS_H

#include "types.h"

/**
 * Root of the binary search tree used for label name resolution.
 * Defined in globals.c; populated by the parser.
 */
extern LabelTree *labeltree;

/**
 * Array of all data-block chain heads parsed from the HeLL source.
 * Defined in globals.c; populated by the parser.
 */
extern DataBlocks datablocks;

/**
 * Array of all code-block chain heads parsed from the HeLL source.
 * Defined in globals.c; populated by the parser.
 */
extern CodeBlocks codeblocks;

/**
 * Non-zero when debug output (a .dbg file) should be generated.
 * Defined in globals.c; set by main() after argument parsing.
 */
extern int debug_mode;

#endif /* LMAO_GLOBALS_H */
