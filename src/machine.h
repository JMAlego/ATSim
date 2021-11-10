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
#ifdef HAS_EXT_IO_REGISTERS
#define EXT_IO_REGISTERS 160
#else
#define EXT_IO_REGISTERS 0
#endif
#define PROG_MEM_SIZE_BYTES (FLASH_SIZE)
#define PROG_MEM_SIZE (PROG_MEM_SIZE_BYTES / 2)
#define DATA_MEM_SIZE (SRAM_SIZE + EXT_IO_REGISTERS + IO_REGISTERS + GP_REGISTERS)
#define PC_MASK (PROG_MEM_SIZE - 1)

// Addresses are inclusive
#define SRAM_START_ADDRESS (GP_REGISTERS + IO_REGISTERS + EXT_IO_REGISTERS)
#define EXT_IO_REGISTERS_START_ADDRESS (GP_REGISTERS + IO_REGISTERS)
#define IO_REGISTERS_START_ADDRESS (GP_REGISTERS)
#define GP_REGISTERS_START_ADDRESS (0)

// Addresses are exclusive
#define SRAM_END_ADDRESS (GP_REGISTERS + IO_REGISTERS + EXT_IO_REGISTERS + SRAM_SIZE)
#define EXT_IO_REGISTERS_END_ADDRESS (GP_REGISTERS + IO_REGISTERS + EXT_IO_REGISTERS)
#define IO_REGISTERS_END_ADDRESS (GP_REGISTERS + IO_REGISTERS)
#define GP_REGISTERS_END_ADDRESS (GP_REGISTERS)

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
#define SetBit(val, bit) ((val) | (0x1 << (bit)))
#define GetBit(val, bit) (((val) & (0x1 << (bit))) >> (bit))
#define TestBit(val, bit) (((val) & (0x1 << (bit))) != 0)
#define ClearBit(val, bit) ((val) & ~(0x1 << (bit)))

#define IsNegative(val, bit_count) (((val) & ((1 << ((bit_count)-1)))) != 0)
#define ToSigned(val, bit_count) (IsNegative(val, bit_count) ? -(((~(val) + 1) & ((1 << (bit_count)) - 1))) : val)

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
#ifdef HAS_EXT_IO_REGISTERS
    Reg8 EXT_IO[EXT_IO_REGISTERS];
#endif
    Mem16 FLASH[FLASH_SIZE / 2];
    Mem8 EEPROM[EEPROM_SIZE];
    Mem8 SRAM[SRAM_SIZE];
    bool SKIP;
} Machine;

void machine_cycle(Machine *m);
void run_until_halt_loop(Machine *m);
void load_memory(Machine *m, uint8_t bytes[], size_t max);
bool load_memory_from_file(Machine *m, const char file_name[]);
void dump_registers(Machine *m);
void dump_stack(Machine *m);
void interactive_break(Machine *m);

#define SetPC(m, a) m->PC = ((a)&PC_MASK)
#define GetPC(m) (m->PC)
#define SetSP(m, a) Set16(m->SP_H, m->SP_L, ((a)&SP_MASK))
#define GetSP(m) (Get16(m->SP_H, m->SP_L) & SP_MASK)

#endif
