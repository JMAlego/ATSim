#include "usi.h"
#include "../config.h"

#ifdef USI_CHARACTER_OUTPUT
#include <stdio.h>
#include <stdbool.h>
#endif

#define REG_USIBR 0x10
#define REG_USIDR 0x0f
#define REG_USISR 0x0e
#define REG_USICR 0x0d

#define BIT_USISR_USISIF 7
#define BIT_USISR_USIOIF 6
#define BIT_USISR_USIPF 5
#define BIT_USISR_USIDC 4
#define BIT_USISR_USICNT3 3
#define BIT_USISR_USICNT2 2
#define BIT_USISR_USICNT1 1
#define BIT_USISR_USICNT0 0

#define BIT_USICR_USISIE 7
#define BIT_USICR_USIOIE 6
#define BIT_USICR_USIWM1 5
#define BIT_USICR_USIWM0 4
#define BIT_USICR_USICS1 3
#define BIT_USICR_USICS0 2
#define BIT_USICR_USICLK 1
#define BIT_USICR_USITC 0

#define USICS_MASK ((1 << BIT_USICR_USICS1) | (1 << BIT_USICR_USICS0))
#define USICS_SHIFT (BIT_USICR_USICS0)

void USI_PreSetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
}

void USI_PostSetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
}

void USI_PreGetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
}

void USI_PostGetDataMem(Machine *m, Address16 address)
{
    UNUSED(m);
    UNUSED(address);
}

#ifdef USI_CHARACTER_OUTPUT
void USI_ShiftChar(Machine *m)
{
    // Quick hacky implementation to get some output...
    static uint8_t output_counter = 0;
    static uint8_t character_buffer = 0;
    const uint8_t usics_value = (m->IO[REG_USICR] & USICS_MASK) >> USICS_SHIFT;
    bool usiclk_value = (m->IO[REG_USICR] & (1 << BIT_USICR_USICLK)) != 0;
    if (usics_value == 1 || ((usics_value == 0) && usiclk_value))
    {
        character_buffer <<= 1;
        character_buffer |= (m->IO[REG_USIDR] & (1 << 7)) >> 7;
        m->IO[REG_USIDR] <<= 1;
        output_counter++;
        if (output_counter >= 8)
        {
            output_counter = 0;
            m->IO[REG_USIBR] = character_buffer;
            putc(character_buffer, stdout);
            character_buffer = 0;
        }
        if (usiclk_value)
        {
            m->IO[REG_USICR] ^= (1 << BIT_USICR_USICLK);
        }
    }
}
#endif

void USI_PostTick(Machine *m)
{
#ifdef USI_CHARACTER_OUTPUT
    USI_ShiftChar(m);
#else

#endif
}
