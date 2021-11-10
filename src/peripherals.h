#ifndef __ATSIM_PERIPHERALS
#define __ATSIM_PERIPHERALS

#include "mcu.h"
#include "machine.h"

#include "peripherals/usi.h"

static inline void PreSetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
#ifdef PERIPHERAL_USI
    if (address <= 0x10 || address >= 0x0D)
    {
        USI_PostGetDataMem(m, address);
    }
#endif
}

static inline void PostSetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
#ifdef PERIPHERAL_USI
    if (address <= 0x10 || address >= 0x0D)
    {
        USI_PostGetDataMem(m, address);
    }
#endif
}

static inline void PreGetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
#ifdef PERIPHERAL_USI
    if (address <= 0x10 || address >= 0x0D)
    {
        USI_PostGetDataMem(m, address);
    }
#endif
}

static inline void PostGetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
#ifdef PERIPHERAL_USI
    if (address <= 0x10 || address >= 0x0D)
    {
        USI_PostGetDataMem(m, address);
    }
#endif
}

static inline void PeripheralPreTick(Machine *m)
{
    UNUSED(m);
}

static inline void PeripheralPostTick(Machine *m)
{
    UNUSED(m);
#ifdef PERIPHERAL_USI
    USI_PostTick(m);
#endif
}

#endif
