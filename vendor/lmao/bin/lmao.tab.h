/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison interface for Yacc-like parsers in C

   Copyright (C) 1984, 1989-1990, 2000-2015, 2018-2021 Free Software Foundation,
   Inc.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <https://www.gnu.org/licenses/>.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.

   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

#ifndef YY_YY_C_DEVELOPMENT_ISYCO_GIT_MALBOLGE_MB_DATABASE_THIRD_PARTY_LMAO_BIN_LMAO_TAB_H_INCLUDED
# define YY_YY_C_DEVELOPMENT_ISYCO_GIT_MALBOLGE_MB_DATABASE_THIRD_PARTY_LMAO_BIN_LMAO_TAB_H_INCLUDED
/* Debug traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif
#if YYDEBUG
extern int yydebug;
#endif

/* Token kinds.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
  enum yytokentype
  {
    YYEMPTY = -2,
    YYEOF = 0,                     /* "end of file"  */
    YYerror = 256,                 /* error  */
    YYUNDEF = 257,                 /* "invalid token"  */
    IDENTIFIER = 258,              /* IDENTIFIER  */
    LABEL = 259,                   /* LABEL  */
    EMPTYLINE = 260,               /* EMPTYLINE  */
    CSEC = 261,                    /* ".CODE"  */
    DSEC = 262,                    /* ".DATA"  */
    RNOP = 263,                    /* RNOP  */
    SLASH = 264,                   /* SLASH  */
    OFFSET = 265,                  /* ".OFFSET or @"  */
    DONTCARE = 266,                /* DONTCARE  */
    NOTUSED = 267,                 /* NOTUSED  */
    BRACKETLEFT = 268,             /* BRACKETLEFT  */
    BRACKETRIGHT = 269,            /* BRACKETRIGHT  */
    COMMA = 270,                   /* COMMA  */
    U_PREFIXED_IDENTIFIER = 271,   /* U_PREFIXED_IDENTIFIER  */
    R_PREFIXED_IDENTIFIER = 272,   /* R_PREFIXED_IDENTIFIER  */
    STRING = 273,                  /* STRING  */
    CONSTANT = 274,                /* CONSTANT  */
    COMMAND = 275,                 /* COMMAND  */
    PLUSMINUS = 276,               /* "+ or -"  */
    MULDIV = 277,                  /* "* or /"  */
    SHIFT = 278,                   /* SHIFT  */
    CRAZY = 279                    /* CRAZY  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
union YYSTYPE
{
#line 306 "C:\\Development\\ISyCo Git\\MALBOLGE-MB-DATABASE\\third_party\\lmao\\src\\lmao.y"

	const char    *s_val;
	unsigned int   i_val;
	unsigned char  c_val;
	unsigned char  prefix;

	XlatCycle *xlat;
	DataAtom  *dataatom;
	DataCell  *datacell;
	DataBlock *datablock;
	CodeBlock *codeblock;

#line 101 "C:\\Development\\ISyCo Git\\MALBOLGE-MB-DATABASE\\third_party\\lmao\\bin\\lmao.tab.h"

};
typedef union YYSTYPE YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif

/* Location type.  */
#if ! defined YYLTYPE && ! defined YYLTYPE_IS_DECLARED
typedef struct YYLTYPE YYLTYPE;
struct YYLTYPE
{
  int first_line;
  int first_column;
  int last_line;
  int last_column;
};
# define YYLTYPE_IS_DECLARED 1
# define YYLTYPE_IS_TRIVIAL 1
#endif


extern YYSTYPE yylval;
extern YYLTYPE yylloc;

int yyparse (void);


#endif /* !YY_YY_C_DEVELOPMENT_ISYCO_GIT_MALBOLGE_MB_DATABASE_THIRD_PARTY_LMAO_BIN_LMAO_TAB_H_INCLUDED  */
