#ifndef __ATSIM_INSTRUCTIONS
#define __ATSIM_INSTRUCTIONS

#include "machine.h"

void decode_and_execute_instruction(Mem16 opcode, Machine *m);

#endif
