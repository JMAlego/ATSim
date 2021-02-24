#ifndef __ATSIM_MACHINE
#define __ATSIM_MACHINE

#include <stdint.h>
#include <stdbool.h>

#define FLASH_SIZE (8 * 1024)
#define EEPROM_SIZE (512)
#define SRAM_SIZE (512)
#define PC_MASK (FLASH_SIZE / 2 - 1)
#define PROG_MEM_SIZE (FLASH_SIZE / 2)
#define GP_REGISTERS 32
#define IO_REGISTERS 64
#define DATA_MEM_SIZE (SRAM_SIZE + IO_REGISTERS + GP_REGISTERS)

typedef uint8_t Reg8;
typedef uint8_t Mem8;
typedef uint16_t Reg16;
typedef uint16_t Mem16;
typedef uint16_t Address16;

#define X_L R[26]
#define X_H R[27]
#define Y_L R[28]
#define Y_H R[29]
#define Z_L R[30]
#define Z_H R[31]

#define Get16(h, l) ((uint16_t)((h << 8) | l))
#define Set16(h, l, v)           \
    do                           \
    {                            \
        h = (((v) >> 8) & 0xff); \
        l = (v)&0xff;            \
    } while (0)

typedef struct
{
    bool C : 1;
    bool Z : 1;
    bool N : 1;
    bool V : 1;
    bool S : 1;
    bool H : 1;
    bool T : 1;
    bool I : 1;
} StatusRegister;

typedef struct
{
    StatusRegister SREG;
    Reg16 PC;
    Reg16 SP;
    Reg8 R[GP_REGISTERS];
    Reg8 IO[IO_REGISTERS];
    Mem16 FLASH[FLASH_SIZE / 2];
    Mem8 EEPROM[EEPROM_SIZE];
    Mem8 SRAM[SRAM_SIZE];
} Machine;

static inline Mem16 GetProgMem(Machine *m, Address16 a)
{
    return m->FLASH[a % PROG_MEM_SIZE];
}

static inline void SetProgMem(Machine *m, Address16 a, Mem16 v)
{
    m->FLASH[a % PROG_MEM_SIZE] = v;
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
        m->IO[(b - GP_REGISTERS) % IO_REGISTERS] = v;
    }
    else if (b < GP_REGISTERS + IO_REGISTERS + SRAM_SIZE)
    {
        m->SRAM[(b - GP_REGISTERS - IO_REGISTERS) % SRAM_SIZE] = v;
    }
}

static inline void ClearStatusFlag(Machine *m, uint8_t index)
{
    switch (index)
    {
    case 7:
        m->SREG.I = 0;
        break;
    case 6:
        m->SREG.T = 0;
        break;
    case 5:
        m->SREG.H = 0;
        break;
    case 4:
        m->SREG.S = 0;
        break;
    case 3:
        m->SREG.V = 0;
        break;
    case 2:
        m->SREG.N = 0;
        break;
    case 1:
        m->SREG.Z = 0;
        break;
    case 0:
        m->SREG.C = 0;
        break;

    default:
        break;
    }
}

static inline void SetStatusFlag(Machine *m, uint8_t index)
{
    switch (index)
    {
    case 7:
        m->SREG.I = 1;
        break;
    case 6:
        m->SREG.T = 1;
        break;
    case 5:
        m->SREG.H = 1;
        break;
    case 4:
        m->SREG.S = 1;
        break;
    case 3:
        m->SREG.V = 1;
        break;
    case 2:
        m->SREG.N = 1;
        break;
    case 1:
        m->SREG.Z = 1;
        break;
    case 0:
        m->SREG.C = 1;
        break;

    default:
        break;
    }
}

static inline bool GetStatusFlag(Machine *m, uint8_t index)
{
    switch (index)
    {
    case 7:
        return m->SREG.I;
    case 6:
        return m->SREG.T;
    case 5:
        return m->SREG.H;
    case 4:
        return m->SREG.S;
    case 3:
        return m->SREG.V;
    case 2:
        return m->SREG.N;
    case 1:
        return m->SREG.Z;
    case 0:
        return m->SREG.C;
    default:
        return 0;
    }
}

#define SetBit(val, bit) (val | (0x1 << bit))
#define GetBit(val, bit) ((val & (0x1 << bit)) >> bit)
#define ClearBit(val, bit) (val & ~(0x1 << bit))

#endif
