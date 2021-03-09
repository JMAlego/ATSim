#ifndef __ATSIM_MCU
#define __ATSIM_MCU

#include "config.h"

#ifdef MCU_ATTiny85

#define MCU "ATTiny85"
#define CORE_TYPE_AVRe

#define FLASH_SIZE (8 * 1024)
#define SRAM_SIZE 512
#define EEPROM_SIZE 512

#define INSTRUCTION_CALL_MISSING
#define INSTRUCTION_JMP_MISSING
#define INSTRUCTION_ELPM_MISSING

#endif

#ifdef CORE_TYPE_AVR
#define INSTRUCTION_BREAK_MISSING
#define INSTRUCTION_CALL_MISSING
#define INSTRUCTION_DES_MISSING
#define INSTRUCTION_EICALL_MISSING
#define INSTRUCTION_EIJMP_MISSING
#define INSTRUCTION_ELPM_MISSING
#define INSTRUCTION_FMUL_MISSING
#define INSTRUCTION_FMULS_MISSING
#define INSTRUCTION_FMULSU_MISSING
#define INSTRUCTION_JMP_MISSING
#define INSTRUCTION_LAC_MISSING
#define INSTRUCTION_LAS_MISSING
#define INSTRUCTION_LAT_MISSING
#define INSTRUCTION_LPM_II_MISSING
#define INSTRUCTION_LPM_III_MISSING
#define INSTRUCTION_MOVW_MISSING
#define INSTRUCTION_MUL_MISSING
#define INSTRUCTION_MULS_MISSING
#define INSTRUCTION_MULSU_MISSING
#define INSTRUCTION_SPM_I_MISSING
#define INSTRUCTION_SPM_II_MISSING
#define INSTRUCTION_SPM_III_MISSING
#define INSTRUCTION_SPM_IV_MISSING
#define INSTRUCTION_SPM_V_MISSING
#define INSTRUCTION_SPMX_I_MISSING
#define INSTRUCTION_SPMX_II_MISSING
#define INSTRUCTION_SPMX_III_MISSING
#define INSTRUCTION_SPMX_IV_MISSING
#define INSTRUCTION_SPMX_V_MISSING
#define INSTRUCTION_SPMX_VI_MISSING
#define INSTRUCTION_SPMX_VII_MISSING
#define INSTRUCTION_SPMX_VIII_MISSING
#define INSTRUCTION_XCH_MISSING
#endif

#ifdef CORE_TYPE_AVRe
#define INSTRUCTION_DES_MISSING
#define INSTRUCTION_EICALL_MISSING
#define INSTRUCTION_EIJMP_MISSING
#define INSTRUCTION_ELPM_MISSING
#define INSTRUCTION_FMUL_MISSING
#define INSTRUCTION_FMULS_MISSING
#define INSTRUCTION_FMULSU_MISSING
#define INSTRUCTION_LAC_MISSING
#define INSTRUCTION_LAS_MISSING
#define INSTRUCTION_LAT_MISSING
#define INSTRUCTION_MUL_MISSING
#define INSTRUCTION_MULS_MISSING
#define INSTRUCTION_MULSU_MISSING
#define INSTRUCTION_SPMX_I_MISSING
#define INSTRUCTION_SPMX_II_MISSING
#define INSTRUCTION_SPMX_III_MISSING
#define INSTRUCTION_SPMX_IV_MISSING
#define INSTRUCTION_SPMX_V_MISSING
#define INSTRUCTION_SPMX_VI_MISSING
#define INSTRUCTION_SPMX_VII_MISSING
#define INSTRUCTION_SPMX_VIII_MISSING
#endif

#endif