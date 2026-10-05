CC    = gcc
CFLAGS = -O3 -Wall -c -I.
LEX   = flex
YACC  = bison -d -v

OBJ = \
	../bin/bison.o \
	../bin/lex.o \
	../bin/globals.o \
	../bin/xlat.o \
	../bin/label.o \
	../bin/layout.o \
	../bin/prefix.o \
	../bin/debug.o \
	../bin/cli.o \
	../bin/main.o \
	../bin/malbolge.o \
	../bin/initialize.o \
	../bin/gen_init.o

all: lmao

../bin:
	mkdir ../bin/

../bin/lmao.tab.c: lmao.y
	$(YACC) -o ../bin/lmao.tab.c lmao.y

../bin/bison.o: ../bin/lmao.tab.c
	$(CC) $(CFLAGS) -o ../bin/bison.o ../bin/lmao.tab.c

../bin/lex.yy.c: lmao.l ../bin/lmao.tab.c
	$(LEX) -o ../bin/lex.yy.c lmao.l

../bin/lex.o: ../bin/lex.yy.c
	$(CC) $(CFLAGS) -o ../bin/lex.o ../bin/lex.yy.c

../bin/%.o: %.c *.h
	$(CC) $(CFLAGS) -o $@ $<

lmao: ../bin $(OBJ)
	gcc $(OBJ) -o ../bin/lmao

clean:
	rm -rf ../bin/
