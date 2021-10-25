CC=avr-gcc
MCU:=attiny85
TARGET := sort
CFLAGS ?= -std=c99 -Wall -Wextra -pedantic -mmcu=$(MCU)
OBJ = $(TARGET).o

.PHONY: all clean assembly

all: $(TARGET).bin

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.s: %.c
	$(CC) $(CFLAGS) -S -o $@ $<

$(TARGET).out: $(TARGET).c $(TARGET).o
	$(CC) $(CFLAGS) -Wl,-Map=$(TARGET).map -o $(TARGET).out $(OBJ)

$(TARGET).bin: $(TARGET).out
	avr-objcopy -O binary $(TARGET).out $(TARGET).bin

assembly: $(TARGET).s

clean:
	rm $(TARGET).out
	rm $(TARGET).o
	rm $(TARGET).bin
