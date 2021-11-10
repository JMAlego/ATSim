#ifndef __ATSIM_PERIPHERAL_USI
#define __ATSIM_PERIPHERAL_USI

#include "../machine.h"

void USI_PreSetDataMem(Machine *m, Address16 address);
void USI_PostSetDataMem(Machine *m, Address16 address);
void USI_PreGetDataMem(Machine *m, Address16 address);
void USI_PostGetDataMem(Machine *m, Address16 address);
void USI_PostTick(Machine *m);

#endif
