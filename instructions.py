#!/usr/bin/env python3.7

import os
from dataclasses import dataclass, field
from math import ceil
from os import path, write
from typing import List, Optional, Set, Tuple

try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal  # type: ignore


def indented(to_indent: str, indent_depth: int = 1, indent_chars: str = "    ") -> str:
    return "{}{}".format(indent_chars * indent_depth, to_indent)


def flag_logic(logic_string, result_var, machine="m"):
    if not set(logic_string).difference(set("0123456789")):
        yield "{} = {};".format(result_var, logic_string)
        return

    if "^" in logic_string:
        left, right, *_ = logic_string.split("^")
        yield "{} = {} != {};".format(result_var, left.strip(), right.strip())
        return

    or_groups = set()
    for or_group in logic_string.split("|"):
        and_items = set()
        for and_item in or_group.split("&"):
            item_result = "{}"
            and_item = and_item.strip()
            invert = False
            if and_item[0] == "!":
                invert = True
                and_item = and_item[1:]
            var = ""
            while and_item and and_item[0] not in set("0123456789"):
                var += and_item[0]
                and_item = and_item[1:]
            if and_item and not set(and_item).difference(set("0123456789")):
                item_result = "TestBit({}, {})".format(var, and_item)
            else:
                item_result = var
            if invert:
                item_result = "!{}".format(item_result)
            and_items.add(item_result)
        or_groups.add("{}".format(" && ".join(sorted(and_items))))
    if len(or_groups) > 1:
        for index, or_group in enumerate(sorted(or_groups), 1):
            yield "const bool {}{} = {};".format(result_var, index, or_group)
        result = "{}".format(" || ".join(
            ["{}{}".format(result_var, x) for x in range(1, 1 + len(or_groups))]))
    else:
        result = or_groups.pop()
    yield "{} = {};".format(result_var, result)


def data_type(bit_width, prefix="uint", postfix="_t"):
    size = 64
    if bit_width <= 8:
        size = 8
    elif bit_width <= 16:
        size = 16
    elif bit_width <= 32:
        size = 32
    return "{}{}{}".format(prefix, size, postfix)


@dataclass
class Variable:
    name: str
    bits: List[int]

    @property
    def bit_width(self):
        return ceil(len(self.bits) / 8.0) * 8

    @property
    def data_type(self):
        return data_type(self.bit_width)

    @property
    def getter(self):
        groups = list()
        for bit in self.bits:
            found_group = False
            for group in groups:
                if bit + 1 in group or bit - 1 in group:
                    group.append(bit)
                    found_group = True
                    break
            if not found_group:
                groups.append([bit])

        group_strings = []
        end_index = 0
        for group in reversed(groups):
            min_index = min(group)
            if min_index != 0:
                if end_index == 0:
                    group_strings.append("((opcode >> {}) & 0x{:x})".format(
                        min_index - end_index, 2**len(group) - 1))
                else:
                    group_strings.append("((opcode >> {}) & (0x{:x} << {}))".format(
                        min_index - end_index, 2**len(group) - 1, end_index))
            else:
                group_strings.append("(opcode & 0x{:x})".format(2**len(group) - 1))
            end_index += len(group)

        bracket_string = "{}"
        if len(group_strings) > 1:
            bracket_string = "({})"

        return bracket_string.format(" | ".join(group_strings))


@dataclass
class Instruction:
    mnemonic: str
    opcode: str
    operation: str
    reads: Optional[Tuple[Tuple[str, str, int], ...]] = None
    writeback: Optional[str] = None
    flag_h: Optional[str] = None
    flag_s: Optional[str] = None
    flag_v: Optional[str] = None
    flag_n: Optional[str] = None
    flag_z: Optional[str] = None
    flag_c: Optional[str] = None
    precondition: Optional[str] = None
    words: int = 1
    pc_post_inc: int = 1
    var_offsets: Optional[Tuple[Tuple[str, int], ...]] = None

    @property
    def plain_opcode(self):
        return self.opcode.replace("_", "")

    @property
    def mask(self):
        bits = "".join("1" if x in ("0", "1") else "0" for x in self.plain_opcode)
        return "0x{:04x}".format(int(bits, 2))

    @property
    def signature(self):
        bits = "".join(x if x in ("0", "1") else "0" for x in self.plain_opcode)
        return "0x{:04x}".format(int(bits, 2))

    @property
    def variables(self):
        result = dict()
        unique_chars = set(filter(lambda x: x not in ("0", "1"), self.plain_opcode))
        for c in sorted(unique_chars):
            bits = list(
                map(lambda x: len(self.plain_opcode) - x[0] - 1,
                    filter(lambda x: x[1] == c, enumerate(self.plain_opcode))))
            result[c] = Variable(c, bits)
        return result

    @property
    def var_reads(self):
        if self.reads:
            for read in self.reads:
                var, index, size = read
                yield "const {} {v}{i} = m->{v}[{i}];".format(data_type(size,
                                                                        prefix="Reg",
                                                                        postfix=""),
                                                              v=var,
                                                              i=index)

    @property
    def checks(self):
        if self.flag_n:
            yield from flag_logic(self.flag_n, "N")

        if self.flag_z:
            if self.flag_z == "_":
                yield "Z = R == 0x00;"
            else:
                yield from flag_logic(self.flag_z, "Z")

        if self.flag_c:
            yield from flag_logic(self.flag_c, "C")

        if self.flag_h:
            yield from flag_logic(self.flag_h, "H")

        if self.flag_v:
            yield from flag_logic(self.flag_v, "V")

        if self.flag_s:
            yield from flag_logic(self.flag_s, "S")

    @property
    def check_reads(self):
        if self.flag_c:
            yield "bool C = m->SREG[SREG_C];"

        if self.flag_z:
            yield "bool Z = m->SREG[SREG_Z];"

        if self.flag_n:
            yield "bool N = m->SREG[SREG_N];"

        if self.flag_v:
            yield "bool V = m->SREG[SREG_V];"

        if self.flag_s:
            yield "bool S = m->SREG[SREG_S];"

        if self.flag_h:
            yield "bool H = m->SREG[SREG_H];"

    @property
    def check_writes(self):
        if self.flag_c:
            yield "m->SREG[SREG_C] = C;"

        if self.flag_z:
            yield "m->SREG[SREG_Z] = Z;"

        if self.flag_n:
            yield "m->SREG[SREG_N] = N;"

        if self.flag_v:
            yield "m->SREG[SREG_V] = V;"

        if self.flag_s:
            yield "m->SREG[SREG_S] = S;"

        if self.flag_h:
            yield "m->SREG[SREG_H] = H;"

    @property
    def code(self):
        yield "static inline void instruction_{}(Machine *m, Mem16 opcode)".format(
            self.mnemonic.lower())
        yield "{"
        yield "#ifdef DEBUG_PRINT_MNEMONICS"
        yield indented('puts("{} {}");'.format(self.mnemonic, self.plain_opcode))
        yield "#endif"
        if any(self.variables):
            yield indented("/* Extract operands from opcode. */")
        if self.var_offsets:
            offsets_dict = dict(self.var_offsets)
        else:
            offsets_dict = {}
        for name, variable in self.variables.items():
            if name in offsets_dict:
                yield indented("const {} {} = {} + {};".format(variable.data_type, name,
                                                               variable.getter, offsets_dict[name]))
            else:
                yield indented("const {} {} = {};".format(variable.data_type, name,
                                                          variable.getter))
            yield "#ifdef DEBUG_PRINT_OPERANDS"
            if name in ("K", ):
                yield indented('printf("  {n} = 0x%04x\\n", {n});'.format(n=name))
            else:
                yield indented('printf("  {n} = %u\\n", {n});'.format(n=name))
            yield "#endif"
        if self.precondition:
            yield indented("/* Assert preconditions. */")
            yield indented("PRECONDITION({});".format(self.precondition))
        if not any(self.variables):
            yield indented("/* No operands in opcode so mark as unused. */")
            yield indented("UNUSED(opcode);")
        if any(self.var_reads):
            yield indented("/* Read vars for operation. */")
        for var_read in self.var_reads:
            yield indented(var_read)
        if any(self.check_reads):
            yield indented("/* Read flags for operation. */")
        for check_read in self.check_reads:
            yield indented(check_read)
        yield indented("/* Perform instruction operation. */")
        yield indented(self.operation)
        if any(self.checks):
            yield indented("/* Update flags. */")
        for check in self.checks:
            yield indented(check)
        if self.writeback:
            yield indented("/* Writeback vars. */")
            yield indented(self.writeback)
        if any(self.check_writes):
            yield indented("/* Writeback flags. */")
        for check_write in self.check_writes:
            yield indented(check_write)
        if self.pc_post_inc != 0:
            yield indented("/* Increment PC. */")
            yield indented("SetPC(m, GetPC(m) + {});".format(self.pc_post_inc))
        yield "}"


INSTRUCTIONS = (
    Instruction(mnemonic="ADC",
                opcode="0001_11rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg8 R = Rd + Rr + (C ? 1 : 0);",
                writeback="m->R[d] = R;",
                flag_h="Rd3 & Rr3 | Rr3 & !R3 | !R3 & Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & Rr7 & !R7 | !Rd7 & !Rr7 & R7",
                flag_n="R7",
                flag_z="_",
                flag_c="Rd7 & Rr7 | Rr7 & !R7 | !R7 & Rd7"),
    Instruction(mnemonic="ADD",
                opcode="0000_11rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg8 R = Rd + Rr;",
                writeback="m->R[d] = R;",
                flag_h="Rd3 & Rr3 | Rr3 & !R3 | !R3 & Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & Rr7 & !R7 | !Rd7 & !Rr7 & R7",
                flag_n="R7",
                flag_z="_",
                flag_c="Rd7 & Rr7 | Rr7 & !R7 | !R7 & Rd7"),
    Instruction(
        mnemonic="AND",
        opcode="0010_00rd_dddd_rrrr",
        reads=(("R", "d", 8), ("R", "r", 8)),
        operation="const Reg8 R = Rd & Rr;",
        writeback="m->R[d] = R;",
        flag_s="N ^ V",
        flag_v="0",
        flag_n="R7",
        flag_z="_",
    ),
    Instruction(
        mnemonic="ANDI",
        opcode="0111_KKKK_dddd_KKKK",
        var_offsets=(("d", 0x10), ),
        reads=(("R", "d", 8), ),
        operation="const Reg8 R = Rd & K;",
        writeback="m->R[d] = R;",
        flag_s="N ^ V",
        flag_v="0",
        flag_n="R7",
        flag_z="_",
    ),
    Instruction(mnemonic="ASR",
                opcode="1001_010d_dddd_0101",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = (Rd >> 1) | (Rd & 0x80);",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="N ^ C",
                flag_n="R7",
                flag_z="_",
                flag_c="Rd0"),
    Instruction(mnemonic="BCLR", opcode="1001_0100_1sss_1000", operation="ClearStatusFlag(m, s);"),
    Instruction(mnemonic="BSET", opcode="1001_0100_0sss_1000", operation="SetStatusFlag(m, s);"),
    Instruction(mnemonic="BLD",
                opcode="1111_100d_dddd_0bbb",
                operation="m->R[d] = m->SREG[SREG_T] ? SetBit(m->R[d], b) : ClearBit(m->R[d], b);"),
    Instruction(mnemonic="BRBC",
                opcode="1111_01kk_kkkk_ksss",
                operation="if(!GetStatusFlag(m, s)) SetPC(m, GetPC(m) + k);"),
    Instruction(mnemonic="BRBS",
                opcode="1111_00kk_kkkk_ksss",
                operation="if(GetStatusFlag(m, s)) SetPC(m, GetPC(m) + k);"),
    Instruction(mnemonic="CBI",
                opcode="1001_1000_AAAA_Abbb",
                operation="m->IO[A] = ClearBit(m->IO[A], b);"),
    Instruction(mnemonic="COM",
                opcode="1001_010d_dddd_0000",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = 0xff - Rd;",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="0",
                flag_n="R7",
                flag_z="_",
                flag_c="1"),
    Instruction(mnemonic="CP",
                opcode="0001_01rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg8 R = Rd - Rr;",
                flag_h="!Rd3 & Rr3 | Rr3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !Rr7 & !R7 | !Rd7 & Rr7 & R7",
                flag_n="R7",
                flag_z="_",
                flag_c="!Rd7 & Rr7 | Rr7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="CPC",
                opcode="0000_01rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg8 R = Rd - Rr - (C ? 1 : 0);",
                flag_h="!Rd3 & Rr3 | Rr3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !Rr7 & !R7 | !Rd7 & Rr7 & R7",
                flag_n="R7",
                flag_z="!R7 & !R6 & !R5 & !R4 & !R3 & !R2 & !R1 & !R0 & Z",
                flag_c="!Rd7 & Rr7 | Rr7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="CPI",
                opcode="0011_KKKK_dddd_KKKK",
                reads=(("R", "d", 8), ),
                var_offsets=(("d", 0x10), ),
                operation="const Reg8 R = Rd - K;",
                flag_h="!Rd3 & K3 | K3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !K7 & !R7 | !K7 & K7 & R7",
                flag_n="R7",
                flag_z="_",
                flag_c="!Rd7 & K7 | K7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="CPSE",
                opcode="0001_00rd_dddd_rrrr",
                operation="if(m->R[d] == m->R[r]) m->SKIP = true;"),
    Instruction(mnemonic="DEC",
                opcode="1001_010d_dddd_1010",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = Rd - 1;",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="!R7 & R6 & R5 & R4 & R3 & R2 & R1 & R0",
                flag_n="R7",
                flag_z="_"),
    Instruction(mnemonic="EOR",
                opcode="0010_01rd_dddd_rrrr",
                operation="const Reg8 R = m->R[d] ^ m->R[r];",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="0",
                flag_n="R7",
                flag_z="_"),
    Instruction(mnemonic="IJMP",
                opcode="1001_0100_0000_1001",
                operation="SetPC(m, Get16(m->Z_H, m->Z_L));"),
    Instruction(mnemonic="IN", opcode="1011_0AAd_dddd_AAAA", operation="m->R[d] = m->IO[A];"),
    Instruction(mnemonic="INC",
                opcode="1001_010d_dddd_0011",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = Rd + 1;",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="R7 & !R6 & !R5 & !R4 & !R3 & !R2 & !R1 & !R0",
                flag_n="R7",
                flag_z="_"),
    Instruction(mnemonic="LD_X_i",
                opcode="1001_000d_dddd_1100",
                operation="m->R[d] = GetDataMem(m, Get16(m->X_H, m->X_L));"),
    Instruction(mnemonic="LD_X_ii",
                opcode="1001_000d_dddd_1101",
                operation="m->R[d] = GetDataMem(m, Get16(m->X_H, m->X_L));",
                writeback="Set16(m->X_H, m->X_L, Get16(m->X_H, m->X_L) + 1);"),
    Instruction(mnemonic="LD_X_iii",
                opcode="1001_000d_dddd_1110",
                operation="Set16(m->X_H, m->X_L, Get16(m->X_H, m->X_L) - 1);",
                writeback="m->R[d] = GetDataMem(m, Get16(m->X_H, m->X_L));"
                ),  # Bit of a hack reordering here but fine as no checks
    Instruction(mnemonic="LD_Y_i",
                opcode="1000_000d_dddd_1000",
                operation="m->R[d] = GetDataMem(m, Get16(m->Y_H, m->Y_L));"),
    Instruction(mnemonic="LD_Y_ii",
                opcode="1001_000d_dddd_1001",
                operation="m->R[d] = GetDataMem(m, Get16(m->Y_H, m->Y_L));",
                writeback="Set16(m->Y_H, m->Y_L, Get16(m->Y_H, m->Y_L) + 1);"),
    Instruction(mnemonic="LD_Y_iii",
                opcode="1001_000d_dddd_1010",
                operation="Set16(m->Y_H, m->Y_L, Get16(m->Y_H, m->Y_L) - 1);",
                writeback="m->R[d] = GetDataMem(m, Get16(m->Y_H, m->Y_L));"
                ),  # Bit of a hack reordering here but fine as no checks
    Instruction(mnemonic="LD_Y_iv",
                opcode="10q0_qq0d_dddd_1qqq",
                operation="m->R[d] = GetDataMem(m, Get16(m->Y_H, m->Y_L) + q);"),
    Instruction(mnemonic="LD_Z_i",
                opcode="1000_000d_dddd_0000",
                operation="m->R[d] = GetDataMem(m, Get16(m->Z_H, m->Z_L));"),
    Instruction(mnemonic="LD_Z_ii",
                opcode="1001_000d_dddd_0001",
                operation="m->R[d] = GetDataMem(m, Get16(m->Z_H, m->Z_L));",
                writeback="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) + 1);"),
    Instruction(mnemonic="LD_Z_iii",
                opcode="1001_000d_dddd_0010",
                operation="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) - 1);",
                writeback="m->R[d] = GetDataMem(m, Get16(m->Z_H, m->Z_L));"
                ),  # Bit of a hack reordering here but fine as no checks
    Instruction(mnemonic="LD_Z_iv",
                opcode="10q0_qq0d_dddd_0qqq",
                operation="m->R[d] = GetDataMem(m, Get16(m->Z_H, m->Z_L) + q);"),
    Instruction(mnemonic="LDI",
                opcode="1110_KKKK_dddd_KKKK",
                var_offsets=(("d", 0x10), ),
                operation="m->R[d] = K;"),
    Instruction(mnemonic="LPM_i",
                opcode="1001_0101_1100_1000",
                operation="m->R[0] = GetProgMemByte(m, Get16(m->Z_H, m->Z_L));"),
    Instruction(mnemonic="LPM_ii",
                opcode="1001_000d_dddd_0100",
                operation="m->R[d] = GetProgMemByte(m, Get16(m->Z_H, m->Z_L));",
                writeback="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) + 1);"),
    Instruction(mnemonic="LPM_iii",
                opcode="1001_000d_dddd_0101",
                operation="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) - 1);",
                writeback="m->R[d] = GetProgMemByte(m, Get16(m->Z_H, m->Z_L));"
                ),  # Bit of a hack reordering here but fine as no checks
    Instruction(mnemonic="LSL",
                opcode="0000_11rd_dddd_rrrr",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = Rd << 1;",
                writeback="m->R[d] = R;",
                precondition="r == d",
                flag_h="Rd3",
                flag_s="N ^ V",
                flag_v="N ^ C",
                flag_n="R7",
                flag_z="_",
                flag_c="Rd7"),
    Instruction(mnemonic="LSR",
                opcode="1001_010d_dddd_0110",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = Rd >> 1;",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="N ^ C",
                flag_n="0",
                flag_z="_",
                flag_c="Rd0"),
    Instruction(mnemonic="MOV", opcode="0010_11rd_dddd_rrrr", operation="m->R[d] = m->R[r];"),
    Instruction(mnemonic="MOVW",
                opcode="0000_0001_dddd_rrrr",
                operation="m->R[(d<<1) + 1] = m->R[(r<<1) + 1];",
                writeback="m->R[d<<1] = m->R[r<<1];"),
    Instruction(mnemonic="MUL",
                opcode="1001_11rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg16 R = Rd * Rr;",
                writeback="Set16(m->R[1], m->R[0], R);",
                flag_c="R15",
                flag_z="_"),
    Instruction(mnemonic="NEG",
                opcode="1001_010d_dddd_0001",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = 0x00 - Rd;",
                writeback="m->R[d] = R;",
                flag_h="R3 | Rd3",
                flag_s="N ^ V",
                flag_v="R7 & !R6 & !R5 & !R4 & !R3 & !R2 & !R1 & !R0",
                flag_n="R7",
                flag_z="_",
                flag_c="R ^ 0x00"),
    Instruction(mnemonic="NOP", opcode="0000_0000_0000_0000", operation="UNUSED(m);"),
    Instruction(
        mnemonic="OR",
        opcode="0010_10rd_dddd_rrrr",
        reads=(("R", "d", 8), ("R", "r", 8)),
        operation="const Reg8 R = Rd | Rr;",
        writeback="m->R[d] = R;",
        flag_s="N ^ V",
        flag_v="0",
        flag_n="R7",
        flag_z="_",
    ),
    Instruction(
        mnemonic="ORI",
        opcode="0110_KKKK_dddd_KKKK",
        var_offsets=(("d", 0x10), ),
        reads=(("R", "d", 8), ),
        operation="const Reg8 R = Rd | K;",
        writeback="m->R[d] = R;",
        flag_s="N ^ V",
        flag_v="0",
        flag_n="R7",
        flag_z="_",
    ),
    Instruction(mnemonic="OUT", opcode="1011_1AAr_rrrr_AAAA", operation="m->IO[A] = m->R[r];"),
    Instruction(mnemonic="POP", opcode="1001_000d_dddd_1111", operation="m->R[d] = PopStack8(m);"),
    Instruction(mnemonic="PUSH",
                opcode="1001_001d_dddd_1111",
                reads=(("R", "d", 8), ),
                operation="PushStack8(m, Rd);"),
    Instruction(mnemonic="RCALL",
                opcode="1101_kkkk_kkkk_kkkk",
                operation="PushStack16(m, m->PC + 1);",
                writeback="SetPC(m, GetPC(m) + ToSigned(k, 12));"),
    Instruction(mnemonic="RET",
                opcode="1001_0101_0000_1000",
                operation="SetPC(m, PopStack16(m));",
                pc_post_inc=0),
    Instruction(mnemonic="RJMP",
                opcode="1100_kkkk_kkkk_kkkk",
                operation="SetPC(m, GetPC(m) + ToSigned(k, 12));"),
    Instruction(mnemonic="ROL",
                opcode="0001_11rd_dddd_rrrr",
                reads=(("R", "d", 8), ),
                precondition="r == d",
                operation="const Reg8 R = (Rd << 1) | (C ? 1 : 0);",
                writeback="m->R[d] = R;",
                flag_h="Rd3",
                flag_s="N ^ V",
                flag_v="N ^ C",
                flag_n="R7",
                flag_z="_",
                flag_c="Rd7"),
    Instruction(mnemonic="ROR",
                opcode="1001_010d_dddd_0111",
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = (Rd >> 1) | (C ? 0x80 : 0);",
                writeback="m->R[d] = R;",
                flag_s="N ^ V",
                flag_v="N ^ C",
                flag_n="R7",
                flag_z="_",
                flag_c="Rd0"),
    Instruction(mnemonic="SBC",
                opcode="0000_10rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg8 R = Rd - Rr - (C ? 1 : 0);",
                writeback="m->R[d] = R;",
                flag_h="!Rd3 & Rr3 | Rr3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !Rr7 & !R7 | !Rd7 & Rr7 & R7",
                flag_n="R7",
                flag_z="(R == 0) && (Z ^ 0)",
                flag_c="!Rd7 & Rr7 | Rr7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="SBCI",
                opcode="0100_KKKK_dddd_KKKK",
                var_offsets=(("d", 0x10), ),
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = Rd - K - (C ? 1 : 0);",
                writeback="m->R[d] = R;",
                flag_h="!Rd3 & K3 | K3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !K7 & !R7 | !Rd7 & K7 & R7",
                flag_n="R7",
                flag_z="(R == 0) && (Z ^ 0)",
                flag_c="!Rd7 & K7 | K7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="SBI",
                opcode="1001_1010_AAAA_Abbb",
                operation="m->IO[A] = SetBit(m->IO[A], b);"),
    Instruction(mnemonic="SBIC",
                opcode="1001_1001_AAAA_Abbb",
                operation="if(!TestBit(m->IO[A], b)) m->SKIP = true;"),
    Instruction(mnemonic="SBIS",
                opcode="1001_1011_AAAA_Abbb",
                operation="if(TestBit(m->IO[A], b)) m->SKIP = true;"),
    Instruction(mnemonic="SBRC",
                opcode="1111_110r_rrrr_0bbb",
                operation="if(!TestBit(m->R[r], b)) m->SKIP = true;"),
    Instruction(mnemonic="SBRS",
                opcode="1111_111r_rrrr_0bbb",
                operation="if(TestBit(m->R[r], b)) m->SKIP = true;"),
    Instruction(mnemonic="ST_X_i",
                opcode="1001_001r_rrrr_1100",
                operation="SetDataMem(m, Get16(m->X_H, m->X_L), m->R[r]);"),
    Instruction(mnemonic="ST_X_ii",
                opcode="1001_001r_rrrr_1101",
                operation="SetDataMem(m, Get16(m->X_H, m->X_L), m->R[r]);",
                writeback="Set16(m->X_H, m->X_L, Get16(m->X_H, m->X_L) + 1);"),
    Instruction(mnemonic="ST_X_iii",
                opcode="1001_001r_rrrr_1110",
                operation="Set16(m->X_H, m->X_L, Get16(m->X_H, m->X_L) - 1);",
                writeback="SetDataMem(m, Get16(m->X_H, m->X_L), m->R[r]);"),
    Instruction(mnemonic="ST_Y_i",
                opcode="1000_001r_rrrr_1000",
                operation="SetDataMem(m, Get16(m->Y_H, m->Y_L), m->R[r]);"),
    Instruction(mnemonic="ST_Y_ii",
                opcode="1001_001r_rrrr_1001",
                operation="SetDataMem(m, Get16(m->Y_H, m->Y_L), m->R[r]);",
                writeback="Set16(m->Y_H, m->Y_L, Get16(m->Y_H, m->Y_L) + 1);"),
    Instruction(mnemonic="ST_Y_iii",
                opcode="1001_001r_rrrr_1010",
                operation="Set16(m->Y_H, m->Y_L, Get16(m->Y_H, m->Y_L) - 1);",
                writeback="SetDataMem(m, Get16(m->Y_H, m->Y_L), m->R[r]);"),
    Instruction(mnemonic="ST_Y_iv",
                opcode="10q0_qq1r_rrrr_1qqq",
                operation="SetDataMem(m, Get16(m->Y_H, m->Y_L) + q, m->R[r]);"),
    Instruction(mnemonic="ST_Z_i",
                opcode="1000_001r_rrrr_0000",
                operation="SetDataMem(m, Get16(m->Z_H, m->Z_L), m->R[r]);"),
    Instruction(mnemonic="ST_Z_ii",
                opcode="1001_001r_rrrr_0001",
                operation="SetDataMem(m, Get16(m->Z_H, m->Z_L), m->R[r]);",
                writeback="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) + 1);"),
    Instruction(mnemonic="ST_Z_iii",
                opcode="1001_001r_rrrr_0010",
                operation="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) - 1);",
                writeback="SetDataMem(m, Get16(m->Z_H, m->Z_L), m->R[r]);"),
    Instruction(mnemonic="ST_Z_iv",
                opcode="10q0_qq1r_rrrr_0qqq",
                operation="SetDataMem(m, Get16(m->Z_H, m->Z_L) + q, m->R[r]);"),
    Instruction(mnemonic="SUB",
                opcode="0001_10rd_dddd_rrrr",
                reads=(("R", "d", 8), ("R", "r", 8)),
                operation="const Reg8 R = Rd - Rr;",
                writeback="m->R[d] = R;",
                flag_h="!Rd3 & Rr3 | Rr3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !Rr7 & !R7 | !Rd7 & Rr7 & R7",
                flag_n="R7",
                flag_z="_",
                flag_c="!Rd7 & Rr7 | Rr7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="SUBI",
                opcode="0101_KKKK_dddd_KKKK",
                var_offsets=(("d", 0x10), ),
                reads=(("R", "d", 8), ),
                operation="const Reg8 R = Rd - K;",
                writeback="m->R[d] = R;",
                flag_h="!Rd3 & K3 | K3 & R3 | R3 & !Rd3",
                flag_s="N ^ V",
                flag_v="Rd7 & !K7 & !R7 | !Rd7 & K7 & R7",
                flag_n="R7",
                flag_z="_",
                flag_c="!Rd7 & K7 | K7 & R7 | R7 & !Rd7"),
    Instruction(mnemonic="SWAP",
                opcode="1001_010d_dddd_0010",
                operation="m->R[d] = ((m->R[d] << 4) & 0x0f) | ((m->R[d] & 0xf0) >> 4);"),
)


def generate_decode_and_execute():
    instruction_tree = {}
    for instruction in INSTRUCTIONS:
        key = (instruction.signature, instruction.mask)
        if key not in instruction_tree:
            instruction_tree[key] = []
        if instruction.precondition:
            instruction_tree[key].insert(0, instruction)
        else:
            instruction_tree[key].append(instruction)

    yield "void decode_and_execute_instruction(Machine *m, Mem16 opcode) {"
    yield indented("const bool skip = m->SKIP;")
    first = True
    for (signature, mask), instructions in instruction_tree.items():
        yield indented("{}if ((opcode & {m}) == {s})".format("" if first else "else ",
                                                             m=mask,
                                                             s=signature))
        first = False
        yield indented("{")
        yield indented("if (skip)", indent_depth=2)
        yield indented("{", indent_depth=2)
        yield indented("SetPC(m, GetPC(m) + {});".format(instructions[0].words), indent_depth=3)
        yield indented("m->SKIP = false;", indent_depth=3)
        yield indented("return;", indent_depth=3)
        yield indented("}", indent_depth=2)
        if len(instructions) == 1:
            yield indented("instruction_{}(m, opcode);".format(instructions[0].mnemonic.lower()),
                           indent_depth=2)
        else:
            first_instruction = True
            for name, variable in instructions[0].variables.items():
                yield indented("const {} {} = {};".format(variable.data_type, name,
                                                          variable.getter),
                               indent_depth=2)
            for instruction in instructions:
                got_else = False
                if instruction.precondition:
                    yield indented("{}if ({})".format("" if first_instruction else "else ",
                                                      instruction.precondition),
                                   indent_depth=2)
                else:
                    got_else = True
                    if not first_instruction:
                        yield indented("else", indent_depth=2)
                    else:
                        yield indented("#warning Unwanted Collision", indent_depth=2)
                yield indented("{", indent_depth=2)
                yield indented("instruction_{}(m, opcode);".format(instruction.mnemonic.lower()),
                               indent_depth=3)
                yield indented("}", indent_depth=2)
                first_instruction = False
                if got_else:
                    break
        yield indented("}")
    yield indented("else")
    yield indented("{")
    yield indented('printf("Warning: Instruction %02x could not be decoded!\\n", opcode);',
                   indent_depth=2)
    yield indented("}")
    yield "}"
    yield ""


def generate_instructions():
    yield "#include \"instructions.h\""
    yield ""
    yield "/* GENERATED CODE */"
    yield "/* This code should be compiled with compiler optimisations turned on. */"
    yield ""
    for instruction in INSTRUCTIONS:
        yield from instruction.code
        yield ""


def main():
    output_path = path.join(os.getcwd(), "src", "instructions.c")
    with open(output_path, "w") as fd:
        for line in generate_instructions():
            fd.write(line)
            fd.write("\r\n")
        for line in generate_decode_and_execute():
            fd.write(line)
            fd.write("\r\n")


if __name__ == "__main__":
    main()
