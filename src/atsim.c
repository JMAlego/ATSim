#include <stdio.h>
#include "machine.h"
#include "machine_accessors.h"

int main(int argc, char* argv[])
{
    // TODO: implement 32 bit instructions like STS

    // Check args
    if (argc != 2)
    {
        puts("Pass single input file.");
        return 1;
    }

    Machine m;

    if(!load_memory_from_file(&m, argv[1]))
    {
        return 1;
    }

    m.PC = 0;
    m.SKIP = false;

    run_until_halt_loop(&m);

    dump_registers(&m);
    dump_stack(&m);

    return 0;
}
