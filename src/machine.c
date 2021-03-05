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
    SetPC(m, GetPC(m) + 1);
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
