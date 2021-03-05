#ifndef __ATSIM_CONFIG
#define __ATSIM_CONFIG

#define UNUSED(x) (void)(x)
#define PRECONDITION(x) UNUSED(x)

#define FLASH_SIZE (8 * 1024)
#define PROG_MEM_SIZE_BYTES (FLASH_SIZE)
#define PROG_MEM_SIZE (PROG_MEM_SIZE_BYTES / 2)

#define PC_MASK (PROG_MEM_SIZE - 1)

#define SRAM_SIZE (512)
#define GP_REGISTERS 32
#define IO_REGISTERS 64
#define DATA_MEM_SIZE (SRAM_SIZE + IO_REGISTERS + GP_REGISTERS)

#define EEPROM_SIZE (512)

#endif
