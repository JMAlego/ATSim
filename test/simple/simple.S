#include <avr/io.h>
.section .text
.global main
main:
    andi r16,0x00
    subi r16,0xff
1:
    rjmp 1b
