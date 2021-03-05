CC=avr-gcc
MCU:=attiny85

TARGET := simple

.PHONY: all

all: $(TARGET).bin

$(TARGET).o: $(TARGET).S
	$(CC) -mmcu=$(MCU) -o $(TARGET).o -c $(TARGET).S

$(TARGET).out: $(TARGET).o
	avr-ld -Tlinker.ld $(TARGET).o -o $(TARGET).out

$(TARGET).bin: $(TARGET).out
	avr-objcopy -O binary $(TARGET).out $(TARGET).bin
