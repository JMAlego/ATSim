#include "machine.h"
#include "instructions.h"
#include "peripherals.h"

Mem16 fetch_instruction(Machine *m)
{
    return GetProgMem(m, m->PC);
}

void machine_cycle(Machine *m)
{
    PeripheralPreTick(m);
    const Mem16 opcode = fetch_instruction(m);
    decode_and_execute_instruction(m, opcode);
    PeripheralPostTick(m);
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

void dump_memory(Machine *m)
{
    puts("- DATA MEMORY -");
    for (uint16_t i = 0; i < DATA_MEM_SIZE; i++)
    {
        printf("DATA[%04x] = %02x\n", i, GetDataMem(m, i));
    }
    puts("- PROG MEMORY -");
    for (uint16_t i = 0; i < PROG_MEM_SIZE; i++)
    {
        printf("PROG[%04x] = %04x\n", i, GetProgMem(m, i));
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

static char _read_char_from_set(const char message[], const char chars[], size_t chars_len)
{
    char read_char = '\0';
    while (true)
    {
        puts(message);
        scanf(" %c", &read_char);
        for (size_t i = 0; i < chars_len; i++)
        {
            if (read_char == chars[i])
            {
                return chars[i];
            }
        }
    }
}

#define read_char_from_set(message, chars) _read_char_from_set(message, chars, sizeof(chars) / sizeof(char))
#define stringify(a) #a

void interactive_view(Machine *m)
{
    const char VALID_OPERATIONS[9] = {'d', 'p', 'r', 'i', 'b', 'w', 'X', 'Y', 'Z'};
    while (true)
    {
        const char read_char = read_char_from_set("view [back=b, data=d, data word=w, program=p, io=i, register=r,X,Y,Z] ",
                                                  VALID_OPERATIONS);
        uint16_t address = 0;
        if (read_char == 'd')
        {
            printf("address [0-%u]\n", DATA_MEM_SIZE - 1);
            scanf(" %hu", &address);
            address = address % DATA_MEM_SIZE;
            printf("DS[%u] = 0x%02x\n", address, GetDataMem(m, address));
        }
        else if (read_char == 'w')
        {
            printf("address [0-%u]\n", DATA_MEM_SIZE - 1);
            scanf(" %hu", &address);
            address = address % DATA_MEM_SIZE;
            printf("DS[%u:%u] = 0x%04x\n",
                   (address + 1) % DATA_MEM_SIZE,
                   address,
                   Get16(GetDataMem(m, (address + 1) % DATA_MEM_SIZE), GetDataMem(m, address)));
        }
        else if (read_char == 'p')
        {
            printf("address [0-%u]\n", PROG_MEM_SIZE - 1);
            scanf(" %hu", &address);
            address = address % PROG_MEM_SIZE;
            printf("PS[%u] = 0x%04x\n", address, GetProgMem(m, address));
        }
        else if (read_char == 'i')
        {
            printf("address [0-%u]\n", IO_REGISTERS - 1);
            scanf(" %hu", &address);
            address = address % IO_REGISTERS;
            printf("IO[%u] = 0x%02x\n", address, m->IO[address]);
        }
        else if (read_char == 'r')
        {
            printf("address [0-%u]\n", GP_REGISTERS - 1);
            scanf(" %hu", &address);
            address = address % GP_REGISTERS;
            printf("R[%u] = 0x%02x\n", address, m->R[address]);
        }
        else if (read_char == 'X')
        {
            printf("R[X] = 0x%04x\n", Get16(m->X_H, m->X_L));
        }
        else if (read_char == 'Y')
        {
            printf("R[Y] = 0x%04x\n", Get16(m->Y_H, m->Y_L));
        }
        else if (read_char == 'Z')
        {
            printf("R[Z] = 0x%04x\n", Get16(m->Z_H, m->Z_L));
        }
        else if (read_char == 'b')
        {
            return;
        }
    }
}

void interactive_break(Machine *m)
{
    const char VALID_OPERATIONS[5] = {'c', 'd', 'v', 'e', 'm'};
    bool continue_debug = true;

    printf("BREAK at PC=0x%04x\n", m->PC);

    while (continue_debug)
    {
        const char read_char = read_char_from_set("break [exit=e, continue=c, dump=d, view=v, m=memdump] ", VALID_OPERATIONS);
        if (read_char == 'c')
        {
            continue_debug = false;
        }
        else if (read_char == 'd')
        {
            dump_registers(m);
            dump_stack(m);
        }
        else if (read_char == 'v')
        {
            interactive_view(m);
        }
        else if (read_char == 'm')
        {
            dump_memory(m);
        }
        else if (read_char == 'e')
        {
            exit(0);
        }
    }
}
