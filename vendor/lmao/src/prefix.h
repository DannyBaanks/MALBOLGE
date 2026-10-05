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

#ifndef LMAO_PREFIX_H
#define LMAO_PREFIX_H

#include "types.h"

/**
 * Resolves all U_ and R_ label prefixes in every data block, and ensures
 * code block chains start at their true head (following prev pointers).
 *
 * For U_<label> <operand>: Computes the relative offset of <operand> within its
 * block and stores it on the DataAtom, then synthesizes virtual NOP CodeBlocks
 * before <label> as needed.
 *
 * For R_<label>: Validates that <label> resolves to a code-section cell that
 * has a successor (i.e. the R_+1 address is valid).
 *
 * \param datablocks  All parsed data-block chains.
 * \param codeblocks  All parsed code-block chains (may have first-element updated).
 * \param labeltree   Label BST for resolving names.
 * \return Non-zero on success; zero if any prefix could not be resolved.
 */
int handle_u_and_r_prefixes(DataBlocks *datablocks, CodeBlocks *codeblocks,
                             LabelTree *labeltree);

#endif /* LMAO_PREFIX_H */
