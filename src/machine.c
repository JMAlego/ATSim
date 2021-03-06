#include "machine.h"
#include "instructions.h"

Mem16 fetch_instruction(Machine *m)
{
    return GetProgMem(m, m->PC);
}

void machine_cycle(Machine *m)
{
    const Mem16 opcode = fetch_instruction(m);
    decode_and_execute_instruction(m, opcode);
}

void run_until_halt_loop(Machine *m)
{
    Reg16 last_pc = 0xffff;
    while (last_pc != m->PC)
    {
        last_pc = m->PC;
        machine_cycle(m);
    }
}

void dump_registers(Machine *m)
{
    puts("- PC & SP -");
    printf("  PC = 0x%04x\n", GetPC(m));
    printf("  SP = 0x%04x\n", GetSP(m));
    puts("- GP Registers -");
    for (uint8_t i = 0; i < GP_REGISTERS; i++)
    {
        printf("  R[%02u] = 0x%02x\n", i, m->R[i]);
    }
    printf("  X     = 0x%04x\n", Get16(m->X_H, m->X_L));
    printf("  Y     = 0x%04x\n", Get16(m->Y_H, m->Y_L));
    printf("  Z     = 0x%04x\n", Get16(m->Z_H, m->Z_L));
}

void dump_stack(Machine *m)
{
    puts("- Stack -");
    puts("  TOS");
    for (uint16_t i = GetSP(m) + 1; i < DATA_MEM_SIZE; i++)
    {
        printf("  STACK[%03u] = %02x\n", DATA_MEM_SIZE - i - 1, GetDataMem(m, i));
    }
    puts("  BOS");
}

void load_memory(Machine *m, uint8_t bytes[], size_t max)
{
    for (size_t word_index = 0; word_index < max / 2; word_index++)
    {
        SetProgMem(m, word_index, Get16(bytes[word_index * 2 + 1], bytes[word_index * 2]));
    }
}

bool load_memory_from_file(Machine *m, const char file_name[])
{
    FILE *fp;
    if (NULL == (fp = fopen(file_name, "rb")))
    {
        fputs("Unable to open input file.\n", stderr);
        return false;
    }

    uint8_t bytes[PROG_MEM_SIZE_BYTES];
    size_t read_bytes = fread(bytes, 1, PROG_MEM_SIZE_BYTES, fp);

    fclose(fp);

    load_memory(m, bytes, read_bytes);

    return true;
}
