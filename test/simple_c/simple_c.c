#include <avr/io.h>
#include <stdint.h>

void main(void)
{
    uint8_t x = 0xf;
    *((char*) 0x1) = x + 1;
    while(1){}
}
