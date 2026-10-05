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

/*
 * This header is kept for backward compatibility.
 * The functions formerly declared here have been moved to dedicated modules:
 *
 *   get_label, print_labeltree           -> label.h
 *   is_valid_initial_character,
 *   is_xlatcycle_existent                -> xlat.h
 *   print_source_positions,
 *   print_xlat2_positions                -> debug.h
 */

#ifndef LMAO_MAIN_H
#define LMAO_MAIN_H

#include "label.h"
#include "xlat.h"
#include "debug.h"

#endif /* LMAO_MAIN_H */
