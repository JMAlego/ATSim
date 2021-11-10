#!/usr/bin/env python3.7
"""Generate instructions.

Writing every instruction by hand would be time consuming and repetitive in C,
so instead we generate the instructions using Python.

The generated instruction implementations are optimised for compiler input not
for readability, as such the output code is rather ugly/contains strange
seemingly pointless intermediary states etc.
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from math import ceil
from os import path
from sys import stderr
from typing import List, Optional, Tuple, Union

try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal  # type: ignore

DEFAULT_OUT_PATH = path.join(path.dirname(__file__), "src", "instructions.c")
DEFAULT_LINE_TERMINATOR = "\r\n"
LINE_TERMINATORS = {
    "rn": "\r\n",
    "n": "\n",
    "r": "\r",
    "nr": "\n\r"  # What are you, some kind of monster?
}


def indented(to_indent: str, indent_depth: int = 1, indent_chars: str = "    ") -> str:
    """Indent the input string."""
    return "{}{}".format(indent_chars * indent_depth, to_indent)


def flag_logic(logic_string, result_var, machine="m"):
    """Expand simplistic flag logic.

    TODO: improve parsing so it's not so ugly.
    """
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
    """Return a datatype based on a target bit width."""
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
    """Represents a variable in an opcode."""

    name: str
    bits: List[int]

    @property
    def bit_width(self):
        """Variable bit width."""
        return ceil(len(self.bits) / 8.0) * 8

    @property
    def data_type(self):
        """Get data type required to store variable."""
        return data_type(self.bit_width)

    def generate_decoder(self, var="opcode"):
        """Generate the C code to decode the variable from an opcode."""
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
                    group_strings.append("(({} >> {}) & 0x{:x})".format(
                        var, min_index - end_index, 2**len(group) - 1))
                else:
                    group_strings.append("(({} >> {}) & (0x{:x} << {}))".format(
                        var, min_index - end_index, 2**len(group) - 1, end_index))
            else:
                group_strings.append("({} & 0x{:x})".format(var, 2**len(group) - 1))
            end_index += len(group)

        bracket_string = "{}"
        if len(group_strings) > 1:
            bracket_string = "({})"

        return bracket_string.format(" | ".join(group_strings))


@dataclass
class Instruction:
    """Represents an instruction.

    TODO: consider different representsation as tonnes of arguments.
    """

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
    pc_post_inc: int = 1
    var_offsets: Optional[Tuple[Union[Tuple[str, int], Tuple[str, int, int]], ...]] = None

    @property
    def is_32bit(self):
        """Return true if this is a double width instruction, false otherwise."""
        return len(self.full_plain_opcode) == 32

    @property
    def words(self):
        """Get number of words in this instruction."""
        return 2 if self.is_32bit else 1

    @property
    def plain_opcode(self):
        """Get plain 16bit opcode."""
        return self.opcode.replace("_", "")[:16]

    @property
    def full_plain_opcode(self):
        """Get plain full opcode.

        This should give 16bits if the instruction is 16 bits, 32 bits if the
        instruction is 32 bits, so on.
        """
        return self.opcode.replace("_", "")[:32]

    @property
    def mask(self):
        """Get bitwise and mask of instruction signature."""
        bits = "".join("1" if x in ("0", "1") else "0" for x in self.plain_opcode)
        return "0x{:04x}".format(int(bits, 2))

    @property
    def signature(self):
        """Get instruction signature.

        This is the value of all bits which are not variable in the opcode.
        """
        bits = "".join(x if x in ("0", "1") else "0" for x in self.plain_opcode)
        return "0x{:04x}".format(int(bits, 2))

    @property
    def variables(self):
        """Get all variables in this instruction's opcode."""
        result = dict()
        unique_chars = set(filter(lambda x: x not in ("0", "1"), self.full_plain_opcode))
        for c in sorted(unique_chars):
            bits = list(
                map(lambda x: len(self.full_plain_opcode) - x[0] - 1,
                    filter(lambda x: x[1] == c, enumerate(self.full_plain_opcode))))
            result[c] = Variable(c, bits)
        return result

    @property
    def var_reads(self):
        """Get the code to read from registers so on as needed by this instruction."""
        if self.reads:
            for read in self.reads:
                var, index, size = read
                if size <= 8:
                    yield "const {} {v}{i} = m->{v}[{i}];".format(data_type(size,
                                                                            prefix="Reg",
                                                                            postfix=""),
                                                                  v=var,
                                                                  i=index)
                elif size <= 16:
                    yield "const {} {v}{i} = m->{v}[{i}] | (m->{v}[{i} + 1] << 8);".format(
                        data_type(size, prefix="Reg", postfix=""), v=var, i=index)

    @property
    def checks(self):
        """Get the code to perform all post-operation flag checks."""
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
        """Get the code to perform pre-operation flag reads."""
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
        """Get the code to perform post-operation flag writes."""
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
        """Get the function which performs this instruction's operation."""
        # Macro to allow removal of instruction in C code
        yield "#ifndef INSTRUCTION_{}_MISSING".format(self.mnemonic.upper())

        # Start of implementation
        yield "static inline void instruction_{}(Machine *m, Mem16 opcode)".format(
            self.mnemonic.lower())
        yield "{"

        # Debug macro sections
        yield "#ifdef DEBUG_PRINT_PC"
        yield indented('printf("PC(w)=%04x, PC(b)=%04x\\n", GetPC(m), GetPC(m)*2);')
        yield "#endif"
        yield "#ifdef DEBUG_PRINT_MNEMONICS"
        yield indented('puts("{} {}");'.format(self.mnemonic, self.full_plain_opcode))
        yield "#endif"

        # Section heading
        if any(self.variables):
            yield indented("/* Extract operands from opcode. */")

        # Get offsets if they exist
        if self.var_offsets:
            offsets_dict = {k: v for k, *v in self.var_offsets}
        else:
            offsets_dict = {}

        # If this is a 32 bit instruction we need to perform a second fetch of a word from memory
        if self.is_32bit:
            yield indented(
                "const Mem32 extended_opcode = (opcode << 16) | GetProgMem(m, ((GetPC(m) + 1) & PC_MASK));"
            )

        # Code to extract variables from opcodes
        for name, variable in self.variables.items():
            decoder = "const {} {} = {{}}{}{{}};".format(
                variable.data_type, name,
                variable.generate_decoder(var="extended_opcode" if self.is_32bit else "opcode"))
            if name in offsets_dict:
                add_val, *mul_val = offsets_dict[name]
                if mul_val:
                    mul_val = mul_val[0]
                    yield indented(
                        decoder.format("({} * ".format(mul_val), ") + {}".format(add_val)))
                else:
                    yield indented(decoder.format("", " + {}".format(add_val)))
            else:
                yield indented(decoder.format("", ""))
            yield "#ifdef DEBUG_PRINT_OPERANDS"
            if name in ("K", ):
                yield indented('printf("  {n} = 0x%04x\\n", {n});'.format(n=name))
            else:
                yield indented('printf("  {n} = %u\\n", {n});'.format(n=name))
            yield "#endif"

        # Macro to assert precondition if it exists for this instruction
        if self.precondition:
            yield indented("/* Assert preconditions. */")
            yield indented("PRECONDITION({});".format(self.precondition))

        # Macro to mark any unused variables as "used" to avoid compiler warnings
        if not any(self.variables):
            yield indented("/* No operands in opcode so mark as unused. */")
            yield indented("UNUSED(opcode);")

        # Section heading
        if any(self.var_reads):
            yield indented("/* Read vars for operation. */")

        # Code to read from registers etc. where needed
        for var_read in self.var_reads:
            yield indented(var_read)

        # Section heading
        if any(self.check_reads):
            yield indented("/* Read flags for operation. */")

        # Read flags before operation
        for check_read in self.check_reads:
            yield indented(check_read)

        # Section heading
        yield indented("/* Perform instruction operation. */")

        # Perform operation of instruction
        yield indented(self.operation)

        # Section heading
        if any(self.checks):
            yield indented("/* Update flags. */")

        # Check for new flag states
        for check in self.checks:
            yield indented(check)

        # If there a "writeback" step, perform it. Sometimes this may be used
        # simply for multiple statement instruction implementations.
        if self.writeback:
            yield indented("/* Writeback vars. */")
            yield indented(self.writeback)

        # Section heading
        if any(self.check_writes):
            yield indented("/* Writeback flags. */")

        # Write flags back
        for check_write in self.check_writes:
            yield indented(check_write)

        # Perform PC post increment/decrement if applicable
        if self.pc_post_inc != 0:
            yield indented("/* Increment PC. */")
            yield indented("SetPC(m, GetPC(m) + {});".format(self.pc_post_inc))

        # End of implementation
        yield "}"

        # If instruction is "missing" then yield no implementation.
        yield "#else"
        yield "static inline void instruction_{}(Machine *m, Mem16 opcode)".format(
            self.mnemonic.lower())
        yield "{"
        # Produce a warning and perform no actual operation
        # NB: this does not increment PC
        yield indented("UNUSED(opcode);")
        yield indented("UNUSED(m);")
        yield indented('puts("Warning: Instruction {} not present on MCU");'.format(
            self.mnemonic.upper()))
        yield "}"
        yield "#endif"


# Instruction definitions
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
    Instruction(mnemonic="ADIW",
                opcode="1001_0110_KKdd_KKKK",
                var_offsets=(("d", 24, 2), ),
                reads=(("R", "d", 16), ),
                operation="const Reg16 R = Rd + K;",
                writeback="Set16(m->R[d+1], m->R[d], R);",
                flag_s="N ^ V",
                flag_v="R15 & !Rd15",
                flag_n="R15",
                flag_z="_",
                flag_c="!R15 & Rd15"),
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
    Instruction(mnemonic="BST",
                opcode="1111_101d_dddd_0bbb",
                operation="m->SREG[SREG_T] = GetBit(m->R[d], b) != 0;"),
    Instruction(mnemonic="BRBC",
                opcode="1111_01kk_kkkk_ksss",
                operation="if(!GetStatusFlag(m, s)) SetPC(m, GetPC(m) + ToSigned(k, 7));"),
    Instruction(mnemonic="BRBS",
                opcode="1111_00kk_kkkk_ksss",
                operation="if(GetStatusFlag(m, s)) SetPC(m, GetPC(m) + ToSigned(k, 7));"),
    Instruction(mnemonic="BREAK", opcode="1001_0101_1001_1000", operation="interactive_break(m);"),
    Instruction(mnemonic="CALL",
                opcode="1001_010k_kkkk_111k_kkkk_kkkk_kkkk_kkkk",
                operation="PushStack16(m, m->PC + 2);",
                writeback="SetPC(m, k);",
                pc_post_inc=0),
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
    Instruction(mnemonic="JMP",
                opcode="1001_010k_kkkk_110k_kkkk_kkkk_kkkk_kkkk",
                operation="SetPC(m, k);",
                pc_post_inc=2),
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
    Instruction(mnemonic="LDS",
                opcode="1001_000d_dddd_0000_kkkk_kkkk_kkkk_kkkk",
                operation="m->R[d] = GetDataMem(m, k);",
                pc_post_inc=2),
    Instruction(mnemonic="LDI",
                opcode="1110_KKKK_dddd_KKKK",
                var_offsets=(("d", 0x10), ),
                operation="m->R[d] = K;"),
    Instruction(mnemonic="LPM_i",
                opcode="1001_0101_1100_1000",
                operation="m->R[0] = GetProgMemByte(m, Get16(m->Z_H, m->Z_L));"),
    Instruction(mnemonic="LPM_ii",
                opcode="1001_000d_dddd_0100",
                operation="m->R[d] = GetProgMemByte(m, Get16(m->Z_H, m->Z_L));"),
    Instruction(mnemonic="LPM_iii",
                opcode="1001_000d_dddd_0101",
                operation="m->R[d] = GetProgMemByte(m, Get16(m->Z_H, m->Z_L));",
                writeback="Set16(m->Z_H, m->Z_L, Get16(m->Z_H, m->Z_L) + 1);"),
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
    Instruction(mnemonic="SBIW",
                opcode="1001_0111_KKdd_KKKK",
                var_offsets=(("d", 24, 2), ),
                reads=(("R", "d", 16), ),
                operation="const Reg16 R = Rd - K;",
                writeback="Set16(m->R[d+1], m->R[d], R);",
                flag_s="N ^ V",
                flag_v="!R15 & Rd15",
                flag_n="R15",
                flag_z="_",
                flag_c="R15 & !Rd15"),
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
    Instruction(mnemonic="STS",
                opcode="1001_001r_rrrr_0000_kkkk_kkkk_kkkk_kkkk",
                operation="SetDataMem(m, k, m->R[r]);",
                pc_post_inc=2),
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
                operation="m->R[d] = ((m->R[d] << 4) & 0xf0) | ((m->R[d] >> 4) & 0x0f);"),
)


def generate_decode_and_execute():
    """Generate the instruction decode and execute logic."""
    # Build a "tree" to find non-unique instructions
    # TODO: Add a second level to group operations that share a mask
    # TODO: Also clean this whole function up XD
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
    # Generate decode logic
    for (signature, mask), instructions in instruction_tree.items():
        yield indented("{}if ((opcode & {m}) == {s})".format("" if first else "else ",
                                                             m=mask,
                                                             s=signature))
        first = False
        yield indented("{")
        # If we need to skip this instruction, do so...
        # This allows skipping of 32 bit instructions.
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
                                                          variable.generate_decoder()),
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
                        # If we get here there's at least 2 instruction definitions which conflict
                        # and don't disambiguate themselves with preconditions.
                        print("Unwanted Collision: Ambiguous instructions...", file=stderr)
                        print([instruction.mnemonic for instruction in instructions], file=stderr)
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
    yield indented(
        'printf("Warning: Instruction %04x at PC=%04x could not be decoded!\\n", opcode, GetPC(m));',
        indent_depth=2)
    yield indented("interactive_break(m);")
    yield indented("}")
    yield "}"
    yield ""


def generate_instructions():
    """Generate instruction implementations."""
    yield "#include \"instructions.h\""
    yield ""
    yield "/* GENERATED CODE */"
    yield "/* This code should be compiled with compiler optimisations turned on. */"
    yield ""
    for instruction in INSTRUCTIONS:
        yield from instruction.code
        yield ""


def main():
    """Entry point function."""
    # Setup arguments
    argument_parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    argument_parser.add_argument("-o",
                                 "--output-path",
                                 type=str,
                                 help="Specify the output path for the generated C file.",
                                 default=DEFAULT_OUT_PATH)
    argument_parser.add_argument("--line-terminator",
                                 choices=LINE_TERMINATORS.keys(),
                                 help="Specify the end of line terminator.",
                                 default="rn")
    parsed_arguments = argument_parser.parse_args()

    # Read arguments
    output_path = parsed_arguments.output_path
    if parsed_arguments.line_terminator in LINE_TERMINATORS:
        line_terminator = LINE_TERMINATORS[parsed_arguments.line_terminator]
    else:
        line_terminator = DEFAULT_LINE_TERMINATOR

    # Generate file
    with open(output_path, "w") as fd:
        for line in generate_instructions():
            fd.write(line)
            fd.write(line_terminator)
        for line in generate_decode_and_execute():
            fd.write(line)
            fd.write(line_terminator)


if __name__ == "__main__":
    main()
