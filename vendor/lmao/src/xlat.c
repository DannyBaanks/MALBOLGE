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

#include "xlat.h"
#include "malbolge.h"

int is_nop(int command) {
	return command != MALBOLGE_COMMAND_OPR
		&& command != MALBOLGE_COMMAND_MOVED
		&& command != MALBOLGE_COMMAND_ROT
		&& command != MALBOLGE_COMMAND_JMP
		&& command != MALBOLGE_COMMAND_OUT
		&& command != MALBOLGE_COMMAND_IN
		&& command != MALBOLGE_COMMAND_HALT;
}

int is_valid_initial_character(int position, char character) {
	int cmd;
	unsigned char u_c = (unsigned char)character;
	if (position < 0 || position >= C2)
		return 0;
	position %= 94;
	if (u_c < 33 || u_c > 126)
		return 0;
	cmd = (position + (int)u_c) % 94;
	return cmd == MALBOLGE_COMMAND_OPR
		|| cmd == MALBOLGE_COMMAND_MOVED
		|| cmd == MALBOLGE_COMMAND_ROT
		|| cmd == MALBOLGE_COMMAND_JMP
		|| cmd == MALBOLGE_COMMAND_OUT
		|| cmd == MALBOLGE_COMMAND_IN
		|| cmd == MALBOLGE_COMMAND_HALT
		|| cmd == MALBOLGE_COMMAND_NOP;
}

int is_xlatcycle_existent(XlatCycle *cycle, int position, char *start_symbol) {
	/*
	 * Algorithm:
	 * 1. Skip leading NOPs, counting them.
	 * 2. Compute the ASCII start character for the first non-NOP command.
	 * 3. Walk the rest of the cycle, applying xlat2 and checking each command.
	 * 4. Verify that the post-cycle NOP prefix also produces NOP commands.
	 * 5. Write *start_symbol (the character that starts the full cycle) if requested.
	 */
	unsigned int prefixed_nops = 0;
	unsigned char first_non_nop_char;
	unsigned char current_char;
	unsigned int i;
	char start_sym_tmp = 0;

	if (cycle == NULL || position < 0 || position >= C2)
		return 0;
	position %= 94;

	/* Non-loop-resistant (no xlat cycle): any position works. */
	if (cycle->next == NULL) {
		if (start_symbol != NULL) {
			*start_symbol = (char)(((cycle->cmd + 94) - position) % 94);
			if (*start_symbol < 33)
				*start_symbol += 94;
		}
		return 1;
	}

	/* Skip leading NOPs in the cycle. */
	while (cycle->cmd == MALBOLGE_COMMAND_NOP
			&& cycle->next != NULL
			&& cycle->next != cycle) {
		cycle = cycle->next;
		prefixed_nops++;
	}

	/* Loop-resistant NOP (RNop): always exists at every position. */
	if (cycle->cmd == MALBOLGE_COMMAND_NOP) {
		/* Lou Scheffer showed immutable NOPs exist at every position. */
		if (start_symbol != NULL) {
			const char * const immutable_nops =
				"FFFFFF>><<::FFFFF3FFFFFF***)))FFFFFFF}FFFFxxFFFrroooFFFFFFF**FF**FFFFFFFFFFFFFFFFPPF**LJJFFFFF";
			*start_symbol = immutable_nops[position];
		}
		return 1;
	}

	/* Compute the ASCII character for the first non-NOP command. */
	first_non_nop_char = (unsigned char)(((cycle->cmd + 94) - position) % 94);
	if (first_non_nop_char < 33)
		first_non_nop_char += 94;
	current_char = first_non_nop_char;

	/* Walk the remainder of the cycle. */
	while (cycle->next != NULL) {
		unsigned char cur_cmd;
		cycle = cycle->next;
		current_char = (unsigned char)XLAT2[(int)current_char - 33];
		cur_cmd = (unsigned char)((current_char + position) % 94);
		if (is_nop(cur_cmd) != is_nop(cycle->cmd))
			return 0;
		if (!is_nop(cur_cmd) && cur_cmd != cycle->cmd)
			return 0;
	}

	/* The character that starts the full cycle (accounting for the NOP prefix). */
	start_sym_tmp = XLAT2[current_char - 33];

	/* Verify that the NOP prefix produces NOP commands after the cycle. */
	for (i = 0; i < prefixed_nops; i++) {
		unsigned char cur_cmd;
		current_char = (unsigned char)XLAT2[current_char - 33];
		cur_cmd = (unsigned char)((current_char + position) % 94);
		if (!is_nop(cur_cmd))
			return 0;
	}

	/* The cycle closes back to first_non_nop_char. */
	if (first_non_nop_char != (unsigned char)XLAT2[current_char - 33])
		return 0;

	if (start_symbol != NULL)
		*start_symbol = start_sym_tmp;

	return 1;
}
