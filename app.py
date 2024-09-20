import argparse
import sys

from model import HandledException
from ui import AppUI


def main():
    if len(sys.argv) == 1:
        AppUI().run()
        return

    # TODO new CLI interface
    # parser = CustomArgumentParser()
    # parser.add_argument("--ignore-previous", action="store_true",
    #                     help="Negeer eerder resultaat, minimaliseer dus niet het aantal wijzigingen")
    # parser.add_argument("--force-xlsx", action="store_true",
    #                     help="Forceer het schrijven van een Excel-bestand ook als er geen wijzigingen zijn")
    # parser.add_argument("--debug", action="store_true", help="Debug mode")
    # parser.add_argument("dirs", nargs="+", help="De directories met de inputbestanden (klassen)")
    #
    # args = parser.parse_args()
    #
    # for directory in args.dirs:
    #     verdeel(directory, args.ignore_previous, args.force_xlsx, args.debug)


class CustomArgumentParser(argparse.ArgumentParser):
    """Customization om de hele help-tekst te printen bij een usage error, en de foutmelding in rood te printen"""

    def error(self, message):
        self.print_help(sys.stderr)
        print(f"\033[91m{self.prog}: error: {message}\033[0m\n", file=sys.stderr)
        self.exit(2)


# def verdeel(directory: str, ignore_previous: bool, force_xlsx: bool, debug: bool):
#     print(f"\nProcessing {directory} {'(ignore previous)' if ignore_previous else ''}")
#     data = load(directory)
#
#     minimize_changes = not ignore_previous and data.previous_result
#     solver = Solver(data, minimize_changes, debug)
#     solver.solve()
#
#     write_csv = True
#     write_xlsx = True
#     if data.previous_result:
#         diffs = data.get_difference_count()
#         if diffs == 0:
#             write_csv = False
#             write_xlsx = force_xlsx
#             print(f"\033[92mNo changes detected, skip writing the csv{"" if write_xlsx else " and xlsx"}\033[0m")
#         else:
#             print(f"\033[93m{diffs} change{'' if diffs == 1 else 's'} detected\033[0m")
#
#     if write_csv:
#         write_to_csv(data, directory)
#
#     if write_xlsx:
#         write_to_excel(data, directory)
#         print(f"\033[92mWrote {directory}/resultaat.xlsx\033[0m")


if __name__ == "__main__":
    try:
        main()
    except HandledException as e:
        print(f"\033[91m{e}\033[0m")
        sys.exit(1)
