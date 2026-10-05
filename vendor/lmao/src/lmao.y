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

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "types.h"
#include "malbolge.h"
#include "globals.h"
#include "label.h"

/*
 * Bison requires YYLTYPE to be declared (or it uses the built-in default).
 * We declare it explicitly so we can copy it to HeLLCodePosition.
 */
#ifndef YYLTYPE_IS_DECLARED
typedef struct YYLTYPE {
	int first_line;
	int first_column;
	int last_line;
	int last_column;
} YYLTYPE;
#define YYLTYPE_IS_DECLARED
#endif

/* Copy a YYLTYPE range into a HeLLCodePosition. */
#define COPY_YYLTYPE_TO_POS(pos, from_start, from_end) \
	do { \
		(pos).first_line   = (from_start).first_line; \
		(pos).first_column = (from_start).first_column; \
		(pos).last_line    = (from_end).last_line; \
		(pos).last_column  = (from_end).last_column; \
	} while (0)

int yyerror(const char *s);
int yylex(void);

/* Insert a label using the parser's current location. */
static int do_insert_label(unsigned char destination_type, void *destination,
                            const char *label, YYLTYPE *loc) {
	HeLLCodePosition pos;
	COPY_YYLTYPE_TO_POS(pos, *loc, *loc);
	return insert_label(destination_type, destination, label, &labeltree, &pos);
}

/* Appends block to the global datablocks array. Returns 1 on success, 0 on OOM. */
static int add_datablock(DataBlock *block) {
	DataBlock **tmp;
	if (block == NULL)
		return 1;
	tmp = (DataBlock **)realloc(datablocks.datafield,
	      (datablocks.size + 1) * sizeof(DataBlock *));
	if (tmp == NULL) {
		yyerror("Out of memory");
		return 0;
	}
	datablocks.datafield = tmp;
	datablocks.datafield[datablocks.size] = block;
	datablocks.size++;
	return 1;
}

/* Appends block to the global codeblocks array. Returns 1 on success, 0 on OOM. */
static int add_codeblock(CodeBlock *block) {
	CodeBlock **tmp;
	if (block == NULL)
		return 1;
	tmp = (CodeBlock **)realloc(codeblocks.codefield,
	      (codeblocks.size + 1) * sizeof(CodeBlock *));
	if (tmp == NULL) {
		yyerror("Out of memory");
		return 0;
	}
	codeblocks.codefield = tmp;
	codeblocks.codefield[codeblocks.size] = block;
	codeblocks.size++;
	return 1;
}

/* Returns the number of backslash-escape sequences in string s. */
static int count_escaped(const char *s) {
	int len = (int)strlen(s);
	int i, count = 0;
	for (i = 0; i < len; i++) {
		if (s[i] == '\\') {
			i++;
			count++;
		}
	}
	return count;
}

/*
 * Decodes a single escape character following a backslash.
 * Returns the decoded byte value.
 */
static int decode_escape(char c) {
	switch (c) {
	case 'n':  return (int)(unsigned char)'\n';
	case 'r':  return (int)(unsigned char)'\r';
	case 't':  return (int)(unsigned char)'\t';
	case '0':  return 0;
	default:   return (int)(unsigned char)c;
	}
}

/*
 * Builds a chain of DataBlocks from the characters of a string literal.
 * Each character becomes one DataBlock with a constant DataCell.
 * The chain is prepended to `next`.
 *
 * \param str      Raw string token including the surrounding quotes.
 * \param next     DataBlock chain to append to the end of the new chain.
 * \param str_loc  Source location of the STRING token.
 * \return Head of the new chain, or next if the string is empty.
 */
static DataBlock *string_to_datablocks(const char *str, DataBlock *next,
                                        YYLTYPE str_loc) {
	int length = (int)strlen(str) - 2; /* exclude surrounding quotes */
	int escaped, processed, i;
	DataBlock *head = NULL;
	DataBlock *prev = NULL;

	if (length <= 0)
		return next;

	escaped   = count_escaped(str);
	processed = 0;

	for (i = 0; i < length; i++) {
		int char_value;
		DataBlock *blk = (DataBlock *)malloc(sizeof(DataBlock));
		DataCell  *cell = (DataCell *)malloc(sizeof(DataCell));
		DataAtom  *atom = (DataAtom *)malloc(sizeof(DataAtom));

		cell->_operator    = DATACELL_OPERATOR_LEAF_ELEMENT;
		cell->left_element  = NULL;
		cell->right_element = NULL;
		cell->leaf_element  = atom;
		atom->destination_label = NULL;
		atom->operand_label     = NULL;

		if (str[i + 1] == '\\') {
			i++;
			char_value = decode_escape(str[i + 1]);
		} else {
			char_value = (int)(unsigned char)str[i + 1];
		}
		atom->number = char_value;
		atom->code_position.first_line   = str_loc.first_line;
		atom->code_position.first_column = str_loc.first_column + i + 1;
		atom->code_position.last_line    = str_loc.first_line;
		atom->code_position.last_column  = str_loc.first_column + i + 1;

		blk->data   = cell;
		blk->offset = -1;
		blk->prev   = prev;
		blk->next   = next;
		if (next != NULL)
			next->prev = blk;
		blk->code_position = atom->code_position;

		/* num_of_blocks: remaining chars (not yet counted) + cells in next chain */
		blk->num_of_blocks = (length - escaped - processed)
		                     + (next != NULL ? next->num_of_blocks : 0);

		if (head == NULL)
			head = blk;
		if (prev != NULL)
			prev->next = blk;
		prev = blk;
		processed++;
	}
	return head;
}

/*
 * Builds an interleaved chain of DataBlocks from the characters of a string
 * literal, with a separator DataCell inserted between every two characters.
 * Layout: char0 sep char1 sep ... charN-1  (no trailing separator)
 * The chain is prepended to `next`.
 *
 * \param str      Raw string token including surrounding quotes.
 * \param sep      DataCell to copy between characters (not freed by this function).
 * \param next     DataBlock chain to append after the new chain.
 * \param str_loc  Source location of the STRING token.
 * \param sep_loc  Source location of the separator expression.
 * \return Head of the new chain, or next if the string is empty.
 */
static DataBlock *string_with_sep_to_datablocks(const char *str,
                                                  DataCell *sep,
                                                  DataBlock *next,
                                                  YYLTYPE str_loc,
                                                  YYLTYPE sep_loc) {
	int length = (int)strlen(str) - 2;
	int escaped, processed, i;
	int total; /* number of DataBlocks to emit: (length-escaped)*2 - 1 */
	DataBlock *head = NULL;
	DataBlock *prev = NULL;

	if (length <= 0)
		return next;

	escaped   = count_escaped(str);
	total     = (length - escaped) * 2 - 1;
	processed = 0;

	for (i = 0; i < total; i++) {
		DataBlock *blk = (DataBlock *)malloc(sizeof(DataBlock));
		DataCell  *cell = (DataCell *)malloc(sizeof(DataCell));

		cell->_operator    = DATACELL_OPERATOR_LEAF_ELEMENT;
		cell->left_element  = NULL;
		cell->right_element = NULL;

		blk->data   = cell;
		blk->offset = -1;
		blk->prev   = prev;
		blk->next   = next;
		if (next != NULL)
			next->prev = blk;

		if (i % 2 == 0) {
			/* Character cell */
			int char_index = i / 2; /* index into the logical (unescaped) char sequence */
			int raw_index  = 0;
			int char_value;
			int k;
			DataAtom *atom = (DataAtom *)malloc(sizeof(DataAtom));

			/* Walk through the raw string to find the char_index-th character,
			 * accounting for escape sequences. */
			for (k = 0; k < char_index; k++) {
				if (str[raw_index + 1] == '\\')
					raw_index += 2;
				else
					raw_index++;
			}
			if (str[raw_index + 1] == '\\') {
				char_value = decode_escape(str[raw_index + 2]);
				raw_index += 2;
			} else {
				char_value = (int)(unsigned char)str[raw_index + 1];
				raw_index++;
			}

			atom->destination_label = NULL;
			atom->operand_label     = NULL;
			atom->number            = char_value;
			atom->code_position.first_line   = str_loc.first_line;
			atom->code_position.first_column = str_loc.first_column + raw_index;
			atom->code_position.last_line    = str_loc.first_line;
			atom->code_position.last_column  = str_loc.first_column + raw_index;
			cell->leaf_element = atom;
			blk->code_position = atom->code_position;
		} else {
			/* Separator cell: copy the separator DataCell */
			memcpy(cell, sep, sizeof(DataCell));
			cell->leaf_element = sep->leaf_element; /* shallow copy is fine */
			blk->code_position.first_line   = sep_loc.first_line;
			blk->code_position.first_column = sep_loc.first_column;
			blk->code_position.last_line    = sep_loc.last_line;
			blk->code_position.last_column  = sep_loc.last_column;
		}

		blk->num_of_blocks = (total - processed)
		                     + (next != NULL ? next->num_of_blocks : 0);

		if (head == NULL)
			head = blk;
		if (prev != NULL)
			prev->next = blk;
		prev = blk;
		processed++;
	}
	return head;
}

YYLTYPE yylloc;
%}

%define parse.lac full
%define parse.error verbose

%union {
	const char    *s_val;
	unsigned int   i_val;
	unsigned char  c_val;
	unsigned char  prefix;

	XlatCycle *xlat;
	DataAtom  *dataatom;
	DataCell  *datacell;
	DataBlock *datablock;
	CodeBlock *codeblock;
}

%token <s_val>  IDENTIFIER
%token <s_val>  LABEL
%token          EMPTYLINE
%token          CSEC ".CODE"
%token          DSEC ".DATA"
%token          RNOP
%token          SLASH
%token          OFFSET ".OFFSET or @"
%token          DONTCARE
%token          NOTUSED
%token          BRACKETLEFT
%token          BRACKETRIGHT
%token          COMMA
%token <s_val>  U_PREFIXED_IDENTIFIER
%token <s_val>  R_PREFIXED_IDENTIFIER
%token <s_val>  STRING
%token <i_val>  CONSTANT
%token <c_val>  COMMAND
%token <c_val>  PLUSMINUS  "+ or -"
%token <c_val>  MULDIV     "* or /"
%token <c_val>  SHIFT
%token          CRAZY

%type <xlat>      XlatCycle
%type <xlat>      Codeexpression
%type <datacell>  Dataexpression
%type <i_val>     Offset
%type <datablock> Dataexpressions
%type <datablock> Datablock
%type <codeblock> Codeexpressions
%type <codeblock> Codeblock
%type <dataatom>  Dataatom
%type <datacell>  Product
%type <datacell>  Crazied
%type <datacell>  Sum

%start Start

%%

Start:
	  EMPTYLINE Start
	| Program
	;

Program:
	  /* empty */
	| Code    Program
	| Data    Program
	;

Code:
	CSEC Codeblocks
	;

Codeblocks:
	  Codeblock                    { if ($1 != NULL && !add_codeblock($1)) return 1; }
	| Codeblocks EMPTYLINE Codeblock { if ($3 != NULL && !add_codeblock($3)) return 1; }
	;

Offset:
	OFFSET CONSTANT IgnoreEmptylines { $$ = $2; }
	;

IgnoreEmptylines:
	  EMPTYLINE IgnoreEmptylines
	| /* empty */
	;

Codeblock:
	  /* empty */                       { $$ = NULL; }
	| Offset LABEL Codeexpressions      {
		if (!do_insert_label(0, $3, $2, &@2)) return 1;
		$$ = $3;
		if ($$ != NULL) $$->offset = $1;
	}
	| LABEL Codeexpressions             {
		if (!do_insert_label(0, $2, $1, &@1)) return 1;
		$$ = $2;
	}
	;

Codeexpressions:
	  /* empty */                       { $$ = NULL; }
	| LABEL Codeexpressions             {
		if (!do_insert_label(0, $2, $1, &@1)) return 1;
		$$ = $2;
	}
	| Codeexpression Codeexpressions    {
		CodeBlock *blk = (CodeBlock *)malloc(sizeof(CodeBlock));
		blk->next         = $2;
		blk->virtual_block = 0;
		if ($2 != NULL) $2->prev = blk;
		blk->prev         = NULL;
		blk->offset       = -1;
		blk->command      = $1;
		blk->num_of_blocks = ($2 == NULL) ? 1 : $2->num_of_blocks + 1;
		COPY_YYLTYPE_TO_POS(blk->code_position, @1, @1);
		$$ = blk;
	}
	;

Codeexpression:
	  RNOP       {
		XlatCycle *cyc = (XlatCycle *)malloc(sizeof(XlatCycle));
		cyc->cmd  = MALBOLGE_COMMAND_NOP;
		cyc->next = cyc; /* loop-resistant NOP links to itself */
		COPY_YYLTYPE_TO_POS(cyc->code_position, @1, @1);
		$$ = cyc;
	}
	| XlatCycle { $$ = $1; }
	;

XlatCycle:
	  COMMAND               {
		XlatCycle *cyc = (XlatCycle *)malloc(sizeof(XlatCycle));
		cyc->next = NULL;
		cyc->cmd  = $1;
		COPY_YYLTYPE_TO_POS(cyc->code_position, @1, @1);
		$$ = cyc;
	}
	| COMMAND SLASH XlatCycle {
		XlatCycle *cyc = (XlatCycle *)malloc(sizeof(XlatCycle));
		cyc->next = $3;
		cyc->cmd  = $1;
		COPY_YYLTYPE_TO_POS(cyc->code_position, @1, @1);
		$$ = cyc;
	}
	;

Data:
	DSEC Datablocks
	;

Datablocks:
	  Datablock                    { if ($1 != NULL && !add_datablock($1)) return 1; }
	| Datablocks EMPTYLINE Datablock { if ($3 != NULL && !add_datablock($3)) return 1; }
	;

Datablock:
	  /* empty */                       { $$ = NULL; }
	| Offset LABEL Dataexpressions      {
		if (!do_insert_label(1, $3, $2, &@2)) return 1;
		$$ = $3;
		$$->offset = $1;
	}
	| LABEL Dataexpressions             {
		if (!do_insert_label(1, $2, $1, &@1)) return 1;
		$$ = $2;
	}
	;

Dataexpressions:
	  /* empty */                       { $$ = NULL; }
	| LABEL Dataexpressions             {
		if (!do_insert_label(1, $2, $1, &@1)) return 1;
		$$ = $2;
	}
	| Dataexpression Dataexpressions    {
		DataBlock *blk = (DataBlock *)malloc(sizeof(DataBlock));
		blk->next          = $2;
		if ($2 != NULL) $2->prev = blk;
		blk->prev          = NULL;
		blk->offset        = -1;
		blk->data          = $1;
		blk->num_of_blocks = ($2 == NULL) ? 1 : $2->num_of_blocks + 1;
		COPY_YYLTYPE_TO_POS(blk->code_position, @1, @1);
		$$ = blk;
	}
	| STRING Dataexpressions            {
		$$ = string_to_datablocks($1, $2, @1);
	}
	| STRING COMMA Dataexpression Dataexpressions {
		$$ = string_with_sep_to_datablocks($1, $3, $4, @1, @3);
	}
	;

Dataatom:
	  CONSTANT              {
		DataAtom *atom = (DataAtom *)malloc(sizeof(DataAtom));
		atom->destination_label = NULL;
		atom->operand_label     = NULL;
		atom->number            = $1;
		COPY_YYLTYPE_TO_POS(atom->code_position, @1, @1);
		$$ = atom;
	}
	| IDENTIFIER            {
		DataAtom *atom = (DataAtom *)malloc(sizeof(DataAtom));
		atom->destination_label = $1;
		atom->operand_label     = NULL;
		atom->number            = 0;
		COPY_YYLTYPE_TO_POS(atom->code_position, @1, @1);
		$$ = atom;
	}
	| R_PREFIXED_IDENTIFIER {
		DataAtom *atom = (DataAtom *)malloc(sizeof(DataAtom));
		atom->destination_label = $1;
		atom->operand_label     = NULL;
		atom->number            = 1; /* R_ prefix: successor offset */
		COPY_YYLTYPE_TO_POS(atom->code_position, @1, @1);
		$$ = atom;
	}
	| U_PREFIXED_IDENTIFIER IDENTIFIER {
		DataAtom *atom = (DataAtom *)malloc(sizeof(DataAtom));
		atom->destination_label = $1;
		atom->operand_label     = $2;
		atom->number            = 0;
		COPY_YYLTYPE_TO_POS(atom->code_position, @1, @2);
		$$ = atom;
	}
	;

Dataexpression:
	  Dataexpression SHIFT Crazied {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = ($2 == '>') ? DATACELL_OPERATOR_ROTATE_R
		                                   : DATACELL_OPERATOR_ROTATE_L;
		cell->left_element  = $1;
		cell->right_element = $3;
		$$ = cell;
	}
	| Crazied               { $$ = $1; }
	| DONTCARE              {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = DATACELL_OPERATOR_DONTCARE;
		cell->left_element  = NULL;
		cell->right_element = NULL;
		$$ = cell;
	}
	| NOTUSED               {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = DATACELL_OPERATOR_NOT_USED;
		cell->left_element  = NULL;
		cell->right_element = NULL;
		$$ = cell;
	}
	;

Crazied:
	  Crazied CRAZY Sum     {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = DATACELL_OPERATOR_CRAZY;
		cell->left_element  = $1;
		cell->right_element = $3;
		$$ = cell;
	}
	| Sum                   { $$ = $1; }
	;

Sum:
	  Sum PLUSMINUS Product  {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = ($2 == '+') ? DATACELL_OPERATOR_PLUS
		                                   : DATACELL_OPERATOR_MINUS;
		cell->left_element  = $1;
		cell->right_element = $3;
		$$ = cell;
	}
	| Product               { $$ = $1; }
	;

Product:
	  Product MULDIV Dataatom {
		DataCell *right = (DataCell *)malloc(sizeof(DataCell));
		right->leaf_element  = $3;
		right->_operator     = DATACELL_OPERATOR_LEAF_ELEMENT;
		right->left_element  = NULL;
		right->right_element = NULL;

		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = ($2 == '*') ? DATACELL_OPERATOR_TIMES
		                                   : DATACELL_OPERATOR_DIVIDE;
		cell->left_element  = $1;
		cell->right_element = right;
		$$ = cell;
	}
	| Product MULDIV BRACKETLEFT Dataexpression BRACKETRIGHT {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = NULL;
		cell->_operator     = ($2 == '*') ? DATACELL_OPERATOR_TIMES
		                                   : DATACELL_OPERATOR_DIVIDE;
		cell->left_element  = $1;
		cell->right_element = $4;
		$$ = cell;
	}
	| Dataatom              {
		DataCell *cell = (DataCell *)malloc(sizeof(DataCell));
		cell->leaf_element  = $1;
		cell->_operator     = DATACELL_OPERATOR_LEAF_ELEMENT;
		cell->left_element  = NULL;
		cell->right_element = NULL;
		$$ = cell;
	}
	| BRACKETLEFT Dataexpression BRACKETRIGHT { $$ = $2; }
	;

%%

int yyerror(const char *s) {
	fprintf(stderr, "Error: %s at line %d column %d.\n",
	        s, yylloc.first_line, yylloc.first_column);
	return 0;
}
