#ifndef __ATSIM_INSTRUCTIONS
#define __ATSIM_INSTRUCTIONS

#include <stdio.h>
#include "machine.h"

void decode_and_execute_instruction(Machine *m, Mem16 opcode);

#endif
