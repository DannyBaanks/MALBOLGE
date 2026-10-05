PREFIX  ?= /usr
BINDIR  := $(PREFIX)/bin
DATADIR := $(PREFIX)/share/lmao

EXAMPLES := \
	example_simple_cat.hell \
	example_simple_hello_world.hell \
	example_hello_world.hell \
	example_cat_halt_on_eof.hell \
	example_digital_root.hell \
	example_adder.hell

.PHONY: all lmao doc install uninstall clean

all: lmao

lmao: bin/lmao
	cp bin/lmao .

bin/lmao: src/*.c src/*.h src/lmao.y src/lmao.l
	$(MAKE) -C src/

doc: Doxyfile src/*.c src/*.h
	doxygen Doxyfile

install: lmao
	install -Dm755 ./lmao                    $(DESTDIR)$(BINDIR)/lmao
	$(foreach f,$(EXAMPLES), \
	    install -Dm644 ./$(f) $(DESTDIR)$(DATADIR)/$(f);)

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/lmao
	$(foreach f,$(EXAMPLES), rm -f $(DESTDIR)$(DATADIR)/$(f);)
	-rmdir $(DESTDIR)$(DATADIR)

clean:
	$(MAKE) -C src/ clean
	rm -f ./lmao
	rm -rf doc/
