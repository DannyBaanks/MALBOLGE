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

#ifndef LMAO_LABEL_H
#define LMAO_LABEL_H

#include "types.h"
#include <stdio.h>

/**
 * Inserts a new label into the label BST.
 *
 * \param destination_type 0 for a code-section label, 1 for a data-section label.
 * \param destination Pointer to the CodeBlock or DataBlock the label refers to.
 *                    Must not be NULL.
 * \param label        Null-terminated label name string.
 * \param labeltree    Pointer to the BST root pointer (may be updated).
 * \param code_pos     Source position of the label definition.
 * \return Non-zero on success, zero on error (e.g. duplicate label).
 */
int insert_label(unsigned char destination_type, void *destination,
                 const char *label, LabelTree **labeltree,
                 const HeLLCodePosition *code_pos);

/**
 * Looks up a label in the BST.
 *
 * Pass NULL for destination_code when you expect a data-section label.
 * Pass NULL for destination_data when you expect a code-section label.
 * Passing both NULL is an error.
 *
 * \param destination_code Receives the CodeBlock pointer (or NULL). May be NULL.
 * \param destination_data Receives the DataBlock pointer (or NULL). May be NULL.
 * \param label            Label name to search for.
 * \param labeltree        Root of the BST.
 * \return Non-zero when the label was found; zero on error or not found.
 */
int get_label(CodeBlock **destination_code, DataBlock **destination_data,
              const char *label, LabelTree *labeltree);

/**
 * Writes all labels and their resolved addresses to the given file.
 * Used for generating the debug output (.dbg file).
 *
 * \param destination Output file.
 * \param labeltree   Root of the BST.
 */
void print_labeltree(FILE *destination, LabelTree *labeltree);

#endif /* LMAO_LABEL_H */
