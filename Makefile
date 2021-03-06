CC = clang
PYTHON ?= python3
CFLAGS ?= -std=c99 -Wall -Wextra -pedantic -O3
CFLAGS_DEPS ?= $(CFLAGS) -MMD -MP
OBJ = $(patsubst src/%.c,obj/%.o,$(wildcard src/*.c))
OBJ_PLUS = $(OBJ) obj/instructions.o
DEPS = $(OBJ:.o=.d)

TARGET := atsim

.PHONY: all run clean instructions

all: bin/$(TARGET) $(OBJ_PLUS)

obj/%.o: src/%.c
	@mkdir -p obj
	$(CC) $(CFLAGS_DEPS) -c -o $@ $<

bin/$(TARGET): src/$(TARGET).c $(OBJ_PLUS)
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/$(TARGET) $(OBJ)

src/instructions.c: instructions.py
	$(PYTHON) instructions.py

instructions: src/instructions.c

run: bin/$(TARGET)
	./bin/$(TARGET) $(ARGS)

clean:
	$(RM) $(OBJ)
	$(RM) $(DEPS)
	$(RM) bin/$(TARGET)

-include $(DEPS)
