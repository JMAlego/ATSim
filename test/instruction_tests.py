"""Run individual instruction tests."""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from os import chdir, devnull, getcwd, listdir, mkdir, path, remove
from shutil import copytree, copy2
from subprocess import CalledProcessError, check_call
from tempfile import TemporaryDirectory
from typing import Iterable, List
from multiprocessing import Pool

TEST_ROOT = path.abspath(path.dirname(__file__))

MAIN_OUTLINE = """\
#include <stdio.h>
#include "machine.h"

#define assert(X) if(!(X)) {{_assertions++; printf("  ASSERTION %zu FAILED: " #X "\\n", _assertions); return 1;}}

int main(void)
{{
    size_t _assertions = 0;
    Machine m;
    load_memory_from_file(&m, "{test_path}/test/{test_name}.bin");
    m.PC = 0;
    m.SKIP = false;
    {pre}
    run_until_halt_loop(&m);
    {post}
    return 0;
}}

"""

TEST_OUTLINE = """\
#include <avr/io.h>
.section .text
.global main
main:
    {test}
halt_loop:
    rjmp halt_loop

"""

TEST_CONFIG = """\
#ifndef __ATSIM_CONFIG
#define __ATSIM_CONFIG

#define MCU_ATTiny85

// #define DEBUG_PRINT_PC
// #define DEBUG_PRINT_MNEMONICS
// #define DEBUG_PRINT_OPERANDS

#endif

"""

TEST_LINKER = """\
SECTIONS
{
  . = 0x0;
  .text : { *(.text) }
}

"""

TEST_MAKEFILE = """\
CC=avr-gcc
MCU:={mcu}

TARGET := {test_name}

.PHONY: all

all: $(TARGET).bin

$(TARGET).o: $(TARGET).S
	$(CC) -mmcu=$(MCU) -o $(TARGET).o -c $(TARGET).S

$(TARGET).out: $(TARGET).o
	avr-ld -Tlinker.ld $(TARGET).o -o $(TARGET).out

$(TARGET).bin: $(TARGET).out
	avr-objcopy -O binary $(TARGET).out $(TARGET).bin

"""


@dataclass
class Test:
    """Represents a testcase."""

    name: str
    precondition: List[str]
    test: List[str]
    postcondition: List[str]

    @staticmethod
    def from_file(file_path: str) -> "Test":
        """Read test from file."""
        name, *_ = path.splitext(path.basename(file_path))

        precondition: List[str] = []
        postcondition: List[str] = []
        test: List[str] = []

        in_precondition = False
        in_postcondition = False
        in_test = False

        with open(file_path, "r") as lines:
            for line in lines:
                line = line.strip()
                if line.startswith("---"):
                    in_precondition = False
                    in_postcondition = False
                    in_test = False

                    split_line = line.split()
                    if len(split_line) < 2:
                        section = ""
                    else:
                        _, section, *_ = split_line
                    section = section.strip()

                    if section == "precondition":
                        in_precondition = True
                    elif section == "postcondition":
                        in_postcondition = True
                    elif section == "test":
                        in_test = True
                elif in_precondition:
                    precondition.append(line)
                elif in_postcondition:
                    postcondition.append(line)
                elif in_test:
                    test.append(line)

        return Test(name, precondition, test, postcondition)


def get_tests() -> Iterable[Test]:
    """Get all tests."""
    test_search_dir = path.join(TEST_ROOT, "instruction_tests")

    for item_name in listdir(test_search_dir):
        full_path = path.join(test_search_dir, item_name)

        if path.isfile(full_path) and path.splitext(full_path)[-1] == ".test":
            yield Test.from_file(full_path)


def run_test(test: Test, parsed_arguments: Namespace, pooled_prefix="") -> int:
    """Run a test."""
    test_dir = test.name

    mkdir(test_dir)

    copytree("../src", path.join(test_dir, "src"))
    copytree("../obj", path.join(test_dir, "obj"))
    copy2("../Makefile", path.join(test_dir, "Makefile"))
    copy2("../instructions.py", path.join(test_dir, "instructions.py"))

    with open(path.join(test_dir, "src", "atsim.c"), "w") as test_c_file:
        test_c_file.write(
            MAIN_OUTLINE.format(test_name=test.name,
                                test_path=test_dir,
                                pre="\n    ".join(test.precondition),
                                post="\n    ".join(test.postcondition)))

    mkdir(path.join(test_dir, "test"))

    with open(path.join(test_dir, "test", "{}.S".format(test.name)), "w") as test_asm_file:
        test_asm_file.write(TEST_OUTLINE.format(test="\n    ".join(test.test)))

    with open(path.join(test_dir, "test", "linker.ld"), "w") as test_asm_linker_file:
        test_asm_linker_file.write(TEST_LINKER)

    with open(path.join(test_dir, "test", "Makefile"), "w") as test_asm_makefile_file:
        test_asm_makefile_file.write(
            TEST_MAKEFILE.format(test_name=test.name, mcu=parsed_arguments.mcu))

    if parsed_arguments.pool < 2:
        print("  Building AVR test...")

    with open(devnull, "w") as null_out:
        try:
            check_call(["make", "-C", path.join(test_dir, "test")], stdout=null_out)
        except CalledProcessError as error:
            if parsed_arguments.pool < 2:
                print("  BUILD FAILURE")
            else:
                print("  {}BUILD '{}' FAILURE".format(pooled_prefix, test.name))
            return error.returncode

        if parsed_arguments.pool < 2:
            print("  Building simulator harness...")
        try:
            check_call([
                "make", "-C", test_dir, "PYTHON={}".format(parsed_arguments.python)
                if parsed_arguments.python else "python3"
            ],
                       stdout=null_out)
        except CalledProcessError as error:
            if parsed_arguments.pool < 2:
                print("  BUILD FAILURE")
            else:
                print("  {}BUILD '{}' FAILURE".format(pooled_prefix, test.name))
            return error.returncode

    if parsed_arguments.pool < 2:
        print("  Executing test...")
    try:
        check_call([path.join(test_dir, "bin", "atsim")])
    except CalledProcessError as error:
        if parsed_arguments.pool < 2:
            print("  TEST FAILURE")
        else:
            print("  {}TEST '{}' FAILURE".format(pooled_prefix, test.name))
        return error.returncode
    if parsed_arguments.pool < 2:
        print("  TEST SUCCESS")
    else:
        print("  {}TEST '{}' SUCCESS".format(pooled_prefix, test.name))

    return 0


def run_test_wrapper(args) -> int:
    """Wrap run_test for pooled execution."""
    return run_test(*args)


def run_tests(test_dir: str, parsed_arguments: Namespace) -> int:
    """Run all tests until a failure, or the end."""
    all_tests = list(get_tests())
    test_count = len(all_tests)
    chdir(path.join(test_dir, "tests"))
    if parsed_arguments.pool > 1:
        print("Running tests with pool of {}...".format(parsed_arguments.pool))
        with Pool(parsed_arguments.pool) as p:
            pool_result = p.map(
                run_test_wrapper,
                [(test, parsed_arguments, "{:03d}/{:03d} ".format(test_index, test_count))
                 for test_index, test in enumerate(all_tests, 1)])
            if any(pool_result):
                return 1
    else:
        for test_index, test in enumerate(all_tests, 1):
            print("{:03d}/{:03d} {}".format(test_index, test_count, test.name))
            result = run_test(test, parsed_arguments)

            if result != 0:
                return result

    return 0


def prebuild(test_dir: str, parsed_arguments: Namespace) -> int:
    """Prebuild the instructions which won't change for each test."""
    original_location = getcwd()
    chdir(test_dir)
    print("Prebuilding shared data...")
    with open(devnull, "w") as null_out:
        try:
            check_call([
                "make", "PYTHON={}".format(parsed_arguments.python)
                if parsed_arguments.python else "python3"
            ],
                       stdout=null_out)
        except CalledProcessError as error:
            print("  BUILD FAILURE")
            return error.returncode
        finally:
            chdir(original_location)
    print("  BUILD SUCCESS")
    return 0


def main() -> int:
    """Entry point."""
    argument_parser = ArgumentParser()

    argument_parser.add_argument("--pool", type=int, default=1)
    argument_parser.add_argument("--mcu", default="attiny85")
    argument_parser.add_argument("--python", default="python3")

    parsed_arguments = argument_parser.parse_args()

    print("Running tests...")

    result_code = 0

    with TemporaryDirectory(prefix="avr_tests") as test_dir:
        copytree(path.join(TEST_ROOT, "../src"), path.join(test_dir, "src"))
        copy2(path.join(TEST_ROOT, "../Makefile"), path.join(test_dir, "Makefile"))
        copy2(path.join(TEST_ROOT, "../instructions.py"), path.join(test_dir, "instructions.py"))
        prebuild(test_dir, parsed_arguments)
        remove(path.join(test_dir, "src", "atsim.c"))
        mkdir(path.join(test_dir, "tests"))
        original_location = getcwd()
        chdir(test_dir)
        result_code = run_tests(test_dir, parsed_arguments)
        chdir(original_location)

    if result_code == 0:
        print("Tests successful!")
    else:
        print("Tests failed!")

    return result_code


if __name__ == "__main__":
    exit(main())
