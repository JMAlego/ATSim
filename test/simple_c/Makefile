CC=avr-gcc
MCU:=attiny85
TARGET := simple_c
CFLAGS ?= -std=c99 -Wall -Wextra -pedantic -mmcu=$(MCU)
OBJ = $(TARGET).o

.PHONY: all clean

all: $(TARGET).bin

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

$(TARGET).out: $(TARGET).c $(TARGET).o
	$(CC) $(CFLAGS) -o $(TARGET).out $(OBJ)

$(TARGET).bin: $(TARGET).out
	avr-objcopy -O binary $(TARGET).out $(TARGET).bin

clean:
	rm $(TARGET).out
	rm $(TARGET).o
	rm $(TARGET).bin
