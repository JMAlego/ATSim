#include <stdio.h>
#include "machine.h"

int main(void)
{
    Machine m;
    load_memory_from_file(&m, "test/simple_c/simple_c.bin");
    m.PC = 0;
    m.SKIP = false;
    run_until_halt_loop(&m);
    dump_registers(&m);
    dump_stack(&m);
    return 0;
}
