#ifndef __ATSIM_MACHINE
#define __ATSIM_MACHINE

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include "mcu.h"

#define UNUSED(x) (void)(x)
#define PRECONDITION(x) UNUSED(x)

#define GP_REGISTERS 32
#define IO_REGISTERS 64
#define PROG_MEM_SIZE_BYTES (FLASH_SIZE)
#define PROG_MEM_SIZE (PROG_MEM_SIZE_BYTES / 2)
#define DATA_MEM_SIZE (SRAM_SIZE + IO_REGISTERS + GP_REGISTERS)
#define PC_MASK (PROG_MEM_SIZE - 1)

typedef uint8_t Reg8;
typedef uint8_t Mem8;
typedef uint16_t Reg16;
typedef uint16_t Mem16;
typedef uint16_t Address16;
typedef uint32_t Mem32;
typedef uint32_t Reg32;

#define X_L R[26]
#define X_H R[27]
#define Y_L R[28]
#define Y_H R[29]
#define Z_L R[30]
#define Z_H R[31]

#define SP_L IO[0x3D]
#define SP_H IO[0x3E]

#define SP_MIN (GP_REGISTERS + IO_REGISTERS)
#if DATA_MEM_SIZE < ((1 << 8) + 1)
#define SP_MASK ((1 << 8) - 1)
#elif DATA_MEM_SIZE < ((1 << 9) + 1)
#define SP_MASK ((1 << 9) - 1)
#elif DATA_MEM_SIZE < ((1 << 10) + 1)
#define SP_MASK ((1 << 10) - 1)
#elif DATA_MEM_SIZE < ((1 << 11) + 1)
#define SP_MASK ((1 << 11) - 1)
#elif DATA_MEM_SIZE < ((1 << 12) + 1)
#define SP_MASK ((1 << 12) - 1)
#elif DATA_MEM_SIZE < ((1 << 13) + 1)
#define SP_MASK ((1 << 13) - 1)
#elif DATA_MEM_SIZE < ((1 << 14) + 1)
#define SP_MASK ((1 << 14) - 1)
#elif DATA_MEM_SIZE < ((1 << 15) + 1)
#define SP_MASK ((1 << 15) - 1)
#else
#define SP_MASK ((1 << 16) - 1)
#endif

#define Get16(h, l) ((uint16_t)(((uint16_t)(h) << 8) | (uint16_t)(l)))
#define Set16(h, l, v)           \
    do                           \
    {                            \
        h = (((v) >> 8) & 0xff); \
        l = (v)&0xff;            \
    } while (0)

/* This could be a bit field but single bit booleans are less efficient on
   most platforms. */
typedef enum
{
    SREG_C = 0,
    SREG_Z = 1,
    SREG_N = 2,
    SREG_V = 3,
    SREG_S = 4,
    SREG_H = 5,
    SREG_T = 6,
    SREG_I = 7,
} StatusRegister;

typedef struct
{
    bool SREG[8];
    Reg16 PC;
    Reg8 R[GP_REGISTERS];
    Reg8 IO[IO_REGISTERS];
    Mem16 FLASH[FLASH_SIZE / 2];
    Mem8 EEPROM[EEPROM_SIZE];
    Mem8 SRAM[SRAM_SIZE];
    bool SKIP;
} Machine;

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

static inline Mem8 GetDataMem(Machine *m, Address16 a)
{
    const Address16 b = a % DATA_MEM_SIZE;
    if (b < GP_REGISTERS)
    {
        return m->R[b % GP_REGISTERS];
    }
    else if (b < GP_REGISTERS + IO_REGISTERS)
    {
        if (b == 0x3F)
        {
            return PackSREG(m);
        }
        return m->IO[(b - GP_REGISTERS) % IO_REGISTERS];
    }
    else if (b < GP_REGISTERS + IO_REGISTERS + SRAM_SIZE)
    {
        return m->SRAM[(b - GP_REGISTERS - IO_REGISTERS) % SRAM_SIZE];
    }

    return 0;
}

static inline void SetDataMem(Machine *m, Address16 a, Mem8 v)
{
    const Address16 b = a % DATA_MEM_SIZE;
    if (b < GP_REGISTERS)
    {
        m->R[b % GP_REGISTERS] = v;
    }
    else if (b < GP_REGISTERS + IO_REGISTERS)
    {
        if (b == 0x3F)
        {
            UnpackSREG(m, v);
        }
        m->IO[(b - GP_REGISTERS) % IO_REGISTERS] = v;
    }
    else if (b < GP_REGISTERS + IO_REGISTERS + SRAM_SIZE)
    {
        m->SRAM[(b - GP_REGISTERS - IO_REGISTERS) % SRAM_SIZE] = v;
    }
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

#define SetPC(m, a) m->PC = ((a)&PC_MASK)
#define GetPC(m) (m->PC)
#define SetSP(m, a) Set16(m->SP_H, m->SP_L, ((a)&SP_MASK))
#define GetSP(m) (Get16(m->SP_H, m->SP_L) & SP_MASK)

static inline void PushStack16(Machine *m, Mem16 val)
{
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

#define SetBit(val, bit) ((val) | (0x1 << (bit)))
#define GetBit(val, bit) (((val) & (0x1 << (bit))) >> (bit))
#define TestBit(val, bit) (((val) & (0x1 << (bit))) != 0)
#define ClearBit(val, bit) ((val) & ~(0x1 << (bit)))

#define IsNegative(val, bit_count) (((val) & ((1 << ((bit_count)-1)))) != 0)
#define ToSigned(val, bit_count) (IsNegative(val, bit_count) ? -(((~(val) + 1) & ((1 << (bit_count - 1)) - 1))) : val)

void machine_cycle(Machine *m);
void run_until_halt_loop(Machine *m);
void load_memory(Machine *m, uint8_t bytes[], size_t max);
bool load_memory_from_file(Machine *m, const char file_name[]);
void dump_registers(Machine *m);
void dump_stack(Machine *m);
void interactive_break(Machine *m);

#endif
