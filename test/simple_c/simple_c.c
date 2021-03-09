#include <avr/io.h>
#include <stdint.h>

void main(void)
{
    uint8_t x = 0x0;
    while(x<255){
        *((char*) 0x1) = x++;
    }
    while(1){}
}
