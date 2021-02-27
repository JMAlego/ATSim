# Instruction Set Simulator for a subset of AVR

## Instructions

### Where do instructions come from?

Instructions are not directly implemented but are instead generated from a more
abstract description of the instruction in Python. The Python code generates a
C implementation for each instruction, which should happen automatically via
make.

### Why do instruction implementations look so strange?

Instruction implementation are optimised to be as efficient as possible with
compiler optimisations enabled. Sadly, this tends to make instructions look
very ugly.

I've tried to ensure that the output of code generation is still human
readable, but it won't be getting any prizes for maintainability (not that it
needs to, being generated). In general it is best to avoid `src/instructions.c`
and consider the descriptions in `instructions.py` instead.

## Disclaimer

This project is not affiliated with Microchip/Atmel in any way. Implementation
is based purely on publicly available documentation for the AVR instruction set
and MCUs which use the instruction set.
