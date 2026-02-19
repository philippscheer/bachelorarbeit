# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


BACHELORARBEIT_PATH = "/root/bachelorarbeit"


class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for Threader
    """

    def executable(self):
        """
        Finds the executable using an absolute path instead of the system PATH.
        """
        # Hardcode the exact absolute path to your target script here:
        target_script = f"{BACHELORARBEIT_PATH}/models/ilp.py"

        # Verify it actually exists before BenchExec tries to run it
        if not os.path.exists(target_script):
            raise FileNotFoundError(
                f"Could not find the target script at {target_script}"
            )

        return target_script

    def working_directory(self, executable):
        """
        Overrides the default BenchExec behavior to set a custom CWD.
        """
        # This dynamically returns the directory that contains your executable
        # (e.g., "/root/bachelorarbeit")
        return os.path.dirname(BACHELORARBEIT_PATH)

    def name(self):
        return "Bachelorarbeit ILP Test"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits=None):
        """
        Constructs the exact command line to be executed.
        - `executable` is the path to the script found above.
        - `tasks` is a list containing the input files matched in your XML.
        """
        # Intentionally leave out 'options' to ensure ONLY the file is passed.
        # This will execute: python3 /path/to/ilp_test.py /path/to/constraint.json
        return ["python3", executable] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parses the tool's output to determine the final status.
        'output' is a list of strings, where each string is a line printed to the terminal.
        """
        # If your script crashed or was forcefully killed, flag it as an error
        if returnsignal == 9 or isTimeout:
            return "TIMEOUT"
        if returncode != 0:
            return f"ERROR (exit code {returncode})"

        # Scan the terminal output for specific keywords printed by your ILP script
        for line in output:
            if "OPTIMAL_SOLUTION_FOUND" in line:
                return benchexec.result.RESULT_DONE  # Standard BenchExec green "Done"
            elif "INFEASIBLE" in line:
                return "INFEASIBLE"  # You can return custom status strings too!
            elif "EXCEPTION" in line or "Traceback" in line:
                return benchexec.result.RESULT_ERROR

        # If the script finishes but we don't see our expected success keywords
        return benchexec.result.RESULT_UNKNOWN
