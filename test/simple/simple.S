#include <avr/io.h>
.section .text
.global main
main:
    ldi r20,85
    out SPL-32,r20
    ldi r20,1
    out SPH-32,r20
    rcall set_1
halt_loop:
    rjmp halt_loop
set_1:
    andi r16,0x00
    subi r16,0xff
    ret
