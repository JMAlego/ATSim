#include <avr/io.h>
#include <stdint.h>

uint16_t fib(uint8_t n)
{
    if(n == 0)
    {
        return 0;
    }
    if(n == 1)
    {
        return 1;
    }
    return fib(n-2) + fib(n-1);
}

void main(void)
{

    *((uint16_t*) 0x1) = fib(24);

    while(1){}
}
