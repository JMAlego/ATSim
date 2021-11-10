#ifndef __ATSIM_MACHINE_ACCESSORS
#define __ATSIM_MACHINE_ACCESSORS

#include "config.h"
#include "machine.h"
#include "peripherals.h"

static inline Mem8 GetProgMemByte(Machine *m, Address16 a)
{
    return (m->FLASH[(a >> 1) % PROG_MEM_SIZE] >> (8 * (a & 0x1))) & 0xff;
}

static inline Mem16 GetProgMem(Machine *m, Address16 a)
{
    return m->FLASH[a % PROG_MEM_SIZE];
}

static inline void SetProgMem(Machine *m, Address16 a, Mem16 v)
{
    m->FLASH[a % PROG_MEM_SIZE] = v;
}

static inline Mem8 PackSREG(Machine *m)
{
    Mem8 SREG = 0;
    SREG |= m->SREG[SREG_I] ? 128 : 0;
    SREG |= m->SREG[SREG_T] ? 64 : 0;
    SREG |= m->SREG[SREG_H] ? 32 : 0;
    SREG |= m->SREG[SREG_S] ? 16 : 0;
    SREG |= m->SREG[SREG_V] ? 8 : 0;
    SREG |= m->SREG[SREG_N] ? 4 : 0;
    SREG |= m->SREG[SREG_Z] ? 2 : 0;
    SREG |= m->SREG[SREG_C] ? 1 : 0;
    return SREG;
}

static inline void UnpackSREG(Machine *m, Mem8 SREG)
{
    m->SREG[SREG_I] = (SREG & 128) != 0;
    m->SREG[SREG_T] = (SREG & 64) != 0;
    m->SREG[SREG_H] = (SREG & 32) != 0;
    m->SREG[SREG_S] = (SREG & 16) != 0;
    m->SREG[SREG_V] = (SREG & 8) != 0;
    m->SREG[SREG_N] = (SREG & 4) != 0;
    m->SREG[SREG_Z] = (SREG & 2) != 0;
    m->SREG[SREG_C] = (SREG & 1) != 0;
}

#define GetRealIndexSRAM(address) (((address) - SRAM_START_ADDRESS) % SRAM_SIZE)
#define GetRealIndexExtendedIOReg(address) (((address) - EXT_IO_REGISTERS_START_ADDRESS) % EXT_IO_REGISTERS)
#define GetRealIndexIOReg(address) (((address) - IO_REGISTERS_START_ADDRESS) % IO_REGISTERS)
#define GetRealIndexGPReg(address) ((address) % GP_REGISTERS)

static inline Mem8 GetDataMem(Machine *m, Address16 a)
{
    const Address16 b = a % DATA_MEM_SIZE;
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
    printf("Read data raw=%u, truncated=%u, real=", a, b);
#endif
    if (b < GP_REGISTERS_END_ADDRESS)
    {
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("R[%u]\n", GetRealIndexGPReg(b));
#endif
        return m->R[GetRealIndexGPReg(b)];
    }
    else if (b < IO_REGISTERS_END_ADDRESS)
    {
        if (b == 0x3F)
        {
            return PackSREG(m);
        }
        PreGetDataMem(m, b);
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("IO[%u]\n", GetRealIndexIOReg(b));
#endif
        const Mem8 r = m->IO[GetRealIndexIOReg(b)];
        PostGetDataMem(m, b);
        return r;
    }
#ifdef HAS_EXT_IO_REGISTERS
    else if (b < EXT_IO_REGISTERS_END_ADDRESS)
    {
        PreGetDataMem(m, b);
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("EXT_IO[%u]\n", GetRealIndexExtendedIOReg(b));
#endif
        const Mem8 r = m->EXT_IO[GetRealIndexExtendedIOReg(b)];
        PostGetDataMem(m, b);
        return r;
    }
#endif
    else if (b < SRAM_END_ADDRESS)
    {
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("SRAM[%u]\n", GetRealIndexSRAM(b));
#endif
        return m->SRAM[GetRealIndexSRAM(b)];
    }

#ifdef DEBUG_TRACE_MEMORY_ACCESSES
    puts("NONE");
#endif
    return 0;
}

static inline void SetDataMem(Machine *m, Address16 a, Mem8 v)
{
    const Address16 b = a % DATA_MEM_SIZE;
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
    printf("Write data raw=%u, truncated=%u, real=", a, b);
#endif
    if (b < GP_REGISTERS_END_ADDRESS)
    {
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("R[%u]\n", GetRealIndexGPReg(b));
#endif
        m->R[GetRealIndexGPReg(b)] = v;
    }
    else if (b < IO_REGISTERS_END_ADDRESS)
    {
        if (b == 0x3F)
        {
            UnpackSREG(m, v);
        }
        PreSetDataMem(m, b);
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("IO[%u]\n", GetRealIndexIOReg(b));
#endif
        m->IO[GetRealIndexIOReg(b)] = v;
        PostSetDataMem(m, b);
    }
#ifdef HAS_EXT_IO_REGISTERS
    else if (b < EXT_IO_REGISTERS_END_ADDRESS)
    {
        PreSetDataMem(m, b);
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("EXT_IO[%u]\n", GetRealIndexExtendedIOReg(b));
#endif
        m->EXT_IO[GetRealIndexExtendedIOReg(b)] = v;
        PostSetDataMem(m, b);
    }
#endif
    else if (b < SRAM_END_ADDRESS)
    {
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
        printf("SRAM[%u]\n", GetRealIndexSRAM(b));
#endif
        m->SRAM[GetRealIndexSRAM(b)] = v;
    }
#ifdef DEBUG_TRACE_MEMORY_ACCESSES
    else
    {
        puts("NONE");
    }
#endif
}

static inline void ClearStatusFlag(Machine *m, uint8_t index)
{
    m->SREG[index & 0x7] = false;
}

static inline void SetStatusFlag(Machine *m, uint8_t index)
{
    m->SREG[index & 0x7] = true;
}

static inline bool GetStatusFlag(Machine *m, uint8_t index)
{
    return m->SREG[index & 0x7];
}

static inline void PushStack16(Machine *m, Mem16 val)
{
#ifdef DEBUG_STACK_COLLISION_DETECTION
    if (GetSP(m) < DEBUG_STACK_COLLISION_DETECTION)
    {
        printf("Warning: stack collision detected at PC=%04x, SP=%04x.\n", GetPC(m), GetSP(m));
        interactive_break(m);
    }
#endif
    SetDataMem(m, GetSP(m), val & 0xff);
    SetDataMem(m, GetSP(m) - 1, (val >> 8) & 0xff);
    SetSP(m, GetSP(m) - 2);
}

static inline Reg16 PopStack16(Machine *m)
{
    SetSP(m, GetSP(m) + 2);
    return GetDataMem(m, GetSP(m)) | (GetDataMem(m, GetSP(m) - 1) << 8);
}

static inline void PushStack8(Machine *m, Mem8 val)
{
    SetDataMem(m, GetSP(m), val);
    SetSP(m, GetSP(m) - 1);
}

static inline Reg8 PopStack8(Machine *m)
{
    SetSP(m, GetSP(m) + 1);
    return GetDataMem(m, GetSP(m));
}

#endif
