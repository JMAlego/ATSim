#!/usr/bin/env python3.7

import os
from dataclasses import dataclass, field
from math import ceil
from os import path
from typing import List, Optional, Set, Tuple

try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal  # type: ignore


def indented(to_indent: str, indent_depth: int = 1, indent_chars: str = "    ") -> str:
    return "{}{}".format(indent_chars * indent_depth, to_indent)


@dataclass
class Variable:
    name: str
    bits: List[int]

    @property
    def bit_width(self):
        return ceil(len(self.bits) / 8.0) * 8

    @property
    def data_type(self):
        if self.bit_width <= 8:
            return "uint8_t"
        elif self.bit_width <= 16:
            return "uint16_t"
        elif self.bit_width <= 32:
            return "uint32_t"
        else:
            return "uint64_t"

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
                group_strings.append("(opcode & 0x{:x})".format(len(group)))
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
    writeback: Optional[str] = None
    check_flags: Set[Literal["H", "S", "V", "N", "Z", "C"]] = field(default_factory=set)
    check_locations: Optional[Tuple[str, ...]] = None
    check_width: int = 8
    check_invert: bool = False
    check_preserve_zero: bool = False

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
        for c in unique_chars:
            bits = list(
                map(lambda x: len(self.plain_opcode) - x[0] - 1,
                    filter(lambda x: x[1] == c, enumerate(self.plain_opcode))))
            result[c] = Variable(c, bits)
        return result

    @property
    def checks(self):
        if "N" in self.check_flags and self.check_locations:
            result_location, *_ = self.check_locations
            yield "m->SREG.N = GetBit({}, {w}) == 0x01;".format(result_location,
                                                                w=self.check_width - 1)

        if "Z" in self.check_flags and self.check_locations:
            result_location, *_ = self.check_locations
            if self.check_preserve_zero:
                yield "m->SREG.Z = ({} == 0x00) && m->SREG.Z;".format(result_location)
            else:
                yield "m->SREG.Z = {} == 0x00;".format(result_location)

        if "C" in self.check_flags and self.check_locations and len(self.check_locations) > 2:
            result_location, source_1, source_2, *_ = self.check_locations
            if self.check_invert:
                yield "const bool C1 = !GetBit({}, {w}) && GetBit({}, {w});".format(
                    source_1, source_2, w=self.check_width - 1)
                yield "const bool C2 = !GetBit({}, {w}) && GetBit({}, {w});".format(
                    source_1, result_location, w=self.check_width - 1)
                yield "const bool C3 = GetBit({}, {w}) && GetBit({}, {w});".format(
                    result_location, source_2, w=self.check_width - 1)
            else:
                yield "const bool C1 = GetBit({}, {w}) && GetBit({}, {w});".format(
                    source_1, source_2, w=self.check_width - 1)
                yield "const bool C2 = GetBit({}, {w}) && !GetBit({}, {w});".format(
                    source_1, result_location, w=self.check_width - 1)
                yield "const bool C3 = !GetBit({}, {w}) && GetBit({}, {w});".format(
                    result_location, source_2, w=self.check_width - 1)
            yield "m->SREG.C = C1 | C2 | C3;"
        elif "C" in self.check_flags and self.check_locations and len(self.check_locations) > 1:
            _, source, *_ = self.check_locations
            yield "m->SREG.C = GetBit({}, 0);".format(source)
        elif "C" in self.check_flags and self.check_locations:
            yield "m->SREG.C = 1;"

        if "H" in self.check_flags and self.check_locations and len(self.check_locations) > 2:
            result_location, source_1, source_2, *_ = self.check_locations
            if self.check_invert:
                yield "const bool H1 = !GetBit({}, {w}) && GetBit({}, {w});".format(
                    source_1, source_2, w=self.check_width // 2 - 1)
                yield "const bool H2 = !GetBit({}, {w}) && GetBit({}, {w});".format(
                    source_1, result_location, w=self.check_width // 2 - 1)
                yield "const bool H3 = GetBit({}, {w}) && GetBit({}, {w});".format(
                    result_location, source_2, w=self.check_width // 2 - 1)
            else:
                yield "const bool H1 = GetBit({}, {w}) && GetBit({}, {w});".format(
                    source_1, source_2, w=self.check_width // 2 - 1)
                yield "const bool H2 = GetBit({}, {w}) && !GetBit({}, {w});".format(
                    source_1, result_location, w=self.check_width // 2 - 1)
                yield "const bool H3 = !GetBit({}, {w}) && GetBit({}, {w});".format(
                    result_location, source_2, w=self.check_width // 2 - 1)
            yield "m->SREG.H = H1 | H2 | H3;"

        if "V" in self.check_flags and self.check_locations and len(self.check_locations) > 2:
            result_location, source_1, source_2, *_ = self.check_locations
            if self.check_invert:
                yield "const bool V1 = !GetBit({}, {w}) && GetBit({}, {w}) && !GetBit({}, {w});".format(
                    result_location, source_1, source_2, w=self.check_width - 1)
                yield "const bool V2 = GetBit({}, {w}) && !GetBit({}, {w}) && GetBit({}, {w});".format(
                    result_location, source_1, source_2, w=self.check_width - 1)
            else:
                yield "const bool V1 = !GetBit({}, {w}) && GetBit({}, {w}) && GetBit({}, {w});".format(
                    result_location, source_1, source_2, w=self.check_width - 1)
                yield "const bool V2 = GetBit({}, {w}) && !GetBit({}, {w}) && !GetBit({}, {w});".format(
                    result_location, source_1, source_2, w=self.check_width - 1)
            yield "m->SREG.V = V1 | V2;"
        elif "V" in self.check_flags and self.check_locations and len(self.check_locations) > 1:
            yield "m->SREG.V = m->SREG.N != m->SREG.C;"
        elif "V" in self.check_flags and self.check_locations:
            yield "m->SREG.V = 0;"

        if "S" in self.check_flags:
            yield "m->SREG.S = m->SREG.N != m->SREG.V;"

    @property
    def code(self):
        yield "void instruction_{}(Mem16 opcode, Machine *m)".format(self.mnemonic.lower())
        yield "{"
        for name, variable in self.variables.items():
            yield indented("const {} {} = {};".format(variable.data_type, name, variable.getter))
        yield indented(self.operation)
        for check in self.checks:
            yield indented(check)
        if self.writeback:
            yield indented(self.writeback)
        yield "}"


INSTRUCTIONS = (
    Instruction(mnemonic="ADC",
                opcode="0001_11rd_dddd_rrrr",
                operation="const Reg8 Rd = m->R[d] + m->R[r] + (m->SREG.C ? 1 : 0);",
                writeback="m->R[d] = Rd;",
                check_flags={"H", "S", "V", "N", "Z", "C"},
                check_locations=("Rd", "m->R[d]", "m->R[r]")),
    Instruction(mnemonic="ADD",
                opcode="0001_11rd_dddd_rrrr",
                operation="const Reg8 Rd = m->R[d] + m->R[r];",
                writeback="m->R[d] = Rd;",
                check_flags={"H", "S", "V", "N", "Z", "C"},
                check_locations=("Rd", "m->R[d]", "m->R[r]")),
    Instruction(mnemonic="AND",
                opcode="0001_11rd_dddd_rrrr",
                operation="const Reg8 Rd = m->R[d] & m->R[r];",
                writeback="m->R[d] = Rd;",
                check_flags={"S", "V", "N", "Z"},
                check_locations=("Rd", "m->R[d]", "m->R[r]")),
    Instruction(mnemonic="ANDI",
                opcode="0111_KKKK_dddd_KKKK",
                operation="const Reg8 Rd = m->R[d] & K;",
                writeback="m->R[d] = Rd;",
                check_flags={"S", "V", "N", "Z"},
                check_locations=("Rd", )),
    Instruction(mnemonic="ASR",
                opcode="1001_010d_dddd_0101",
                operation="const Reg8 Rd = (m->R[d] >> 1) | (m->R[d] & 0x80);",
                writeback="m->R[d] = Rd;",
                check_flags={"S", "V", "N", "Z", "C"},
                check_locations=("Rd", "m->R[d]")),
    Instruction(mnemonic="BCLR", opcode="1001_0100_1sss_1000", operation="ClearStatusFlag(m, s);"),
    Instruction(mnemonic="BSET", opcode="1001_0100_0sss_1000", operation="SetStatusFlag(m, s);"),
    Instruction(mnemonic="BLD",
                opcode="1111_100d_dddd_0bbb",
                operation="m->R[d] = m->SREG.T ? SetBit(m->R[d], b) : ClearBit(m->R[d], b);"),
    Instruction(mnemonic="BRBC",
                opcode="1111_01kk_kkkk_ksss",
                operation="if(!GetStatusFlag(m, s)) m->PC = (m->PC + k) & PC_MASK;"),
    Instruction(mnemonic="BRBS",
                opcode="1111_00kk_kkkk_ksss",
                operation="if(GetStatusFlag(m, s)) m->PC = (m->PC + k) & PC_MASK;"),
    Instruction(mnemonic="CBI",
                opcode="1001_1000_AAAA_Abbb",
                operation="m->IO[A] = ClearBit(m->IO[A], b);"),
    Instruction(mnemonic="COM",
                opcode="1001_010d_dddd_0000",
                operation="const Reg8 Rd = 0xff - m->R[d];",
                writeback="m->R[d] = Rd;",
                check_flags={"S", "V", "N", "Z", "C"},
                check_locations=("Rd", )),
    Instruction(mnemonic="CP",
                opcode="0001_01rd_dddd_rrrr",
                operation="const Reg8 R = m->R[d] - m->R[r];",
                check_flags={"H", "S", "V", "N", "Z", "C"},
                check_locations=("R", "m->R[d]", "m->R[r]"),
                check_invert=True),
    Instruction(mnemonic="CPC",
                opcode="0000_01rd_dddd_rrrr",
                operation="const Reg8 R = m->R[d] - m->R[r] - (m->SREG.C ? 1 : 0);",
                check_flags={"H", "S", "V", "N", "Z", "C"},
                check_locations=("R", "m->R[d]", "m->R[r]"),
                check_invert=True,
                check_preserve_zero=True),
)


def generate_instructions():
    yield "#include \"instructions.h\""
    yield ""
    for instruction in INSTRUCTIONS:
        yield from instruction.code
        yield ""


def main():
    output_path = path.join(os.getcwd(), "src", "instructions.c")
    with open(output_path, "w") as fd:
        fd.write("\r\n".join(generate_instructions()))


if __name__ == "__main__":
    main()
