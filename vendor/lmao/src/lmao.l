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

%option noyywrap
%option nounput
%option noinput
%option yylineno

%{
#include "types.h"
#include "malbolge.h"
#include "globals.h"

/* Include the Bison-generated token definitions. */
#include "lmao.tab.h"

/*
 * Returning 1 from yylex() signals a fatal lexer error to yyparse().
 * We use a macro to make error-exit points explicit in the rules below.
 */
#define LEXER_ABORT return 1

#ifndef YYLTYPE_IS_DECLARED
typedef struct YYLTYPE {
	int first_line;
	int first_column;
	int last_line;
	int last_column;
} YYLTYPE;
#define YYLTYPE_IS_DECLARED
#endif
extern YYLTYPE yylloc;

/* Position of the last seen '{', for error messages. */
static YYLTYPE last_curly_bracket;

/* Update yylloc with the position of the current token. */
static void update_loc(void) {
	static int curr_line = 1;
	static int curr_col  = 1;
	const char *s;

	yylloc.first_line   = curr_line;
	yylloc.first_column = curr_col;

	for (s = yytext; *s != '\0'; s++) {
		if (*s == '\n') {
			curr_line++;
			curr_col = 1;
		} else {
			curr_col++;
		}
	}

	yylloc.last_line   = curr_line;
	yylloc.last_column = curr_col - 1;
}

#define YY_USER_ACTION update_loc();

int yyerror(const char *s);

/*
 * require_whitespace: set to 1 after tokens that must be separated by
 * whitespace from the next token. Cleared on any whitespace or punctuation.
 */
static int require_whitespace = 0;

/*
 * in_data_section: 1 while lexing a .DATA block; 0 in a .CODE block.
 * Controls whether '/' is SLASH or MULDIV.
 */
static int in_data_section = 0;

#define CHECK_WHITESPACE() \
	do { \
		if (require_whitespace) { \
			yyerror("Misformed identifier"); \
			LEXER_ABORT; \
		} \
	} while (0)

#define REQUIRE_WHITESPACE() require_whitespace = 1

/*
 * suppress_emptyline: 1 while inside a '{ ... }' block.
 * Suppresses blank-line EMPTYLINE tokens and section headers.
 */
static char suppress_emptyline = 0;
%}

trit        [0-2]
tritail     ({trit}){1,10}
trinary     0t{tritail}
digit       [0-9]
decimal     0*{digit}{1,5}
chr         [!-&(-\[\]-~ ]|\\'|\\n|\\r|\\t|\\\\
character   '({chr})'
constant    C0|C1|C20|C21|C2|EOF
command     MovD|Nop|Jmp|In|Out|Opr|Rot|Hlt
identifier  [A-Za-z_][0-9A-Za-z_]{0,99}
label       {identifier}:
whitespace  [ \t\r]
comment     ([;%#]|\/\/)[^\n]*|\/\*\/*(([^\*\/]\/*)*\*+)+\/
part        [\n]{whitespace}*[\n]
section     \.(CODE|DATA)
offset      \.OFFSET|@
uprefixed   U_{identifier}
rprefixed   R_{identifier}
string      \"(\\.|[^\"\\\r\n])*\"

%%

{comment}   { /* discard */ }

{string}    {
	CHECK_WHITESPACE();
	yylval.s_val = strdup(yytext);
	REQUIRE_WHITESPACE();
	return STRING;
}

,           { require_whitespace = 0; return COMMA; }

{character} {
	CHECK_WHITESPACE();
	if (yytext[1] == '\\') {
		switch (yytext[2]) {
		case 'n':  yylval.i_val = '\n'; break;
		case 'r':  yylval.i_val = '\r'; break;
		case 't':  yylval.i_val = '\t'; break;
		case '\\': yylval.i_val = '\\'; break;
		default:   yylval.i_val = (unsigned char)yytext[2]; break;
		}
	} else {
		yylval.i_val = (unsigned char)yytext[1];
	}
	REQUIRE_WHITESPACE();
	return CONSTANT;
}

\{          {
	require_whitespace = 0;
	if (suppress_emptyline == 0) {
		suppress_emptyline = 1;
		last_curly_bracket = yylloc;
		return EMPTYLINE;
	} else {
		yyerror("Opening curly bracket found, but previous curly bracket has not been closed");
		fprintf(stderr, "Previous curly bracket was at line %d column %d.\n",
		        last_curly_bracket.first_line, last_curly_bracket.first_column);
		LEXER_ABORT;
	}
}

\}          {
	require_whitespace = 0;
	if (suppress_emptyline == 1) {
		suppress_emptyline = 0;
		last_curly_bracket = yylloc;
		return EMPTYLINE;
	} else {
		yyerror("Closing curly bracket without opening curly bracket found");
		LEXER_ABORT;
	}
}

{trinary}   {
	unsigned short num = 0;
	unsigned char pos = 2;
	CHECK_WHITESPACE();
	for (; yytext[pos] != '\0'; pos++) {
		num *= 3;
		num += yytext[pos] - '0';
	}
	yylval.i_val = num;
	REQUIRE_WHITESPACE();
	return CONSTANT;
}

{decimal}   {
	unsigned int num = 0;
	unsigned char pos = 0;
	CHECK_WHITESPACE();
	for (; yytext[pos] != '\0'; pos++) {
		num *= 10;
		num += yytext[pos] - '0';
	}
	if (num > 59048) { yyerror("Integer too big"); LEXER_ABORT; }
	yylval.i_val = num;
	REQUIRE_WHITESPACE();
	return CONSTANT;
}

{constant}  {
	CHECK_WHITESPACE();
	if (yytext[0] == 'E')       yylval.i_val = 59048; /* EOF  */
	else if (yytext[1] == '0')  yylval.i_val = 0;     /* C0   */
	else if (yytext[1] == '1')  yylval.i_val = 29524; /* C1   */
	else if (yytext[2] == '\0') yylval.i_val = 59048; /* C2   */
	else if (yytext[2] == '0')  yylval.i_val = 59046; /* C20  */
	else                        yylval.i_val = 59047; /* C21  */
	REQUIRE_WHITESPACE();
	return CONSTANT;
}

RNop        {
	CHECK_WHITESPACE();
	REQUIRE_WHITESPACE();
	return RNOP;
}

{command}:  { yyerror("Label must not be a Malbolge command"); LEXER_ABORT; }

{command}   {
	CHECK_WHITESPACE();
	if      (!strncmp(yytext, "Nop",  4)) yylval.c_val = MALBOLGE_COMMAND_NOP;
	else if (!strncmp(yytext, "MovD", 5)) yylval.c_val = MALBOLGE_COMMAND_MOVED;
	else if (!strncmp(yytext, "Jmp",  4)) yylval.c_val = MALBOLGE_COMMAND_JMP;
	else if (!strncmp(yytext, "In",   3)) yylval.c_val = MALBOLGE_COMMAND_IN;
	else if (!strncmp(yytext, "Out",  4)) yylval.c_val = MALBOLGE_COMMAND_OUT;
	else if (!strncmp(yytext, "Hlt",  4)) yylval.c_val = MALBOLGE_COMMAND_HALT;
	else if (!strncmp(yytext, "Opr",  4)) yylval.c_val = MALBOLGE_COMMAND_OPR;
	else if (!strncmp(yytext, "Rot",  4)) yylval.c_val = MALBOLGE_COMMAND_ROT;
	else { yyerror("Internal error"); LEXER_ABORT; }
	REQUIRE_WHITESPACE();
	return COMMAND;
}

{uprefixed}:  { yyerror("Label must not start with U_"); LEXER_ABORT; }
{rprefixed}:  { yyerror("Label must not start with R_"); LEXER_ABORT; }

{label}     {
	char identifier[101];
	int len = (int)strlen(yytext);
	CHECK_WHITESPACE();
	memcpy(identifier, yytext, len - 1);
	identifier[len - 1] = '\0'; /* strip trailing colon */
	yylval.s_val = strdup(identifier);
	return LABEL;
}

{uprefixed} {
	CHECK_WHITESPACE();
	yylval.s_val = strdup(yytext + 2); /* strip "U_" prefix */
	REQUIRE_WHITESPACE();
	return U_PREFIXED_IDENTIFIER;
}

{rprefixed} {
	CHECK_WHITESPACE();
	yylval.s_val = strdup(yytext + 2); /* strip "R_" prefix */
	REQUIRE_WHITESPACE();
	return R_PREFIXED_IDENTIFIER;
}

{identifier} {
	CHECK_WHITESPACE();
	yylval.s_val = strdup(yytext);
	REQUIRE_WHITESPACE();
	return IDENTIFIER;
}

\/          {
	require_whitespace = 0;
	if (in_data_section) {
		yylval.c_val = '/';
		return MULDIV;
	}
	return SLASH;
}

{section}   {
	if (suppress_emptyline == 0) {
		CHECK_WHITESPACE();
		REQUIRE_WHITESPACE();
		if (yytext[1] == 'C') {
			in_data_section = 0;
			return CSEC;
		} else {
			in_data_section = 1;
			return DSEC;
		}
	} else {
		if (yytext[1] == 'C')
			yyerror("Unexpected .CODE inside curly brackets");
		else
			yyerror("Unexpected .DATA inside curly brackets");
		LEXER_ABORT;
	}
}

({part})+   {
	require_whitespace = 0;
	if (suppress_emptyline == 0)
		return EMPTYLINE;
}

{offset}    {
	if (yytext[0] != '@') {
		CHECK_WHITESPACE();
		REQUIRE_WHITESPACE();
	} else {
		require_whitespace = 0;
	}
	return OFFSET;
}

\?\-?       {
	CHECK_WHITESPACE();
	REQUIRE_WHITESPACE();
	if (yytext[1] == '-' && !debug_mode)
		return NOTUSED;
	return DONTCARE;
}

\+|-        { yylval.c_val = yytext[0]; require_whitespace = 0; return PLUSMINUS; }

\*          { yylval.c_val = '*';       require_whitespace = 0; return MULDIV; }

>>|<<       { yylval.c_val = yytext[0]; require_whitespace = 0; return SHIFT; }

!           { require_whitespace = 0; return CRAZY; }

\(          { return BRACKETLEFT; }
\)          { return BRACKETRIGHT; }

{whitespace} { require_whitespace = 0; }

\n           { require_whitespace = 0; }

<<EOF>>     {
	if (suppress_emptyline == 1) {
		yyerror("Missing closing curly bracket at EOF");
		fprintf(stderr, "Opening curly bracket was at line %d column %d.\n",
		        last_curly_bracket.first_line, last_curly_bracket.first_column);
		LEXER_ABORT;
	} else {
		yyterminate();
	}
}

.           { yyerror("Unexpected character"); LEXER_ABORT; }
