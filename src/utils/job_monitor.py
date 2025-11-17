import time

from src.utils.logger import log_func, log_section


def _find_solution_progress_section(lines: list[str]) -> int:
    """Find the index of the SOLUTION PROGRESS section."""
    for i, line in enumerate(lines):
        if "SOLUTION PROGRESS" in line:
            return i
    return -1


def _is_header_line(line: str) -> bool:
    """Check if line is an unwanted header line."""
    return (
        (line.startswith("STEP") and "ORIGIN" in line)
        or (line.startswith("STEP") and "TOTAL" in line and "WALL" in line)
        or (line.startswith("INCREMENT") and "TIME" in line)
    )


def _is_increment_data_line(line: str) -> bool:
    """Check if line contains increment data."""
    return line and line[0].isdigit() and "E+" in line and "E-" in line


def _should_skip_line(line: str) -> bool:
    """Check if line should be skipped from output."""
    return line.startswith("INSTANCE WITH CRITICAL") or line.startswith(
        "Output Field Frame"
    )


def _parse_increment_data(values: list[str]) -> dict:
    """Parse increment data from split line values."""
    return {
        "increment": int(values[0]),
        "step_time": float(values[1]),
        "total_time": float(values[2]),
        "wall_time": values[3],
        "stable_inc": float(values[4]),
        "kinetic_energy": float(values[6]),
        "total_energy": float(values[7]),
    }


def _print_header():
    """Print the formatted table header."""
    log_section(
        f"{'Inc':<8} {'Step Time':<12} {'Wall Time':<10} {'Stable Inc':<12} {'KE':<10} {'Total E':<10}"
    )


def _print_increment_data(data: dict):
    """Print formatted increment data."""
    log_func(
        f"{data['increment']:<8} {data['step_time']:<12.4e} {data['wall_time']:<10} "
        f"{data['stable_inc']:<12.4e} {data['kinetic_energy']:<10.3e} {data['total_energy']:<10.3e}"
    )


def _check_ke_minimum(
    kinetic_energy: float, previous_ke: float, min_ke: float, ke_increasing_count: int
) -> tuple[float, int, bool]:
    """Check if kinetic energy has reached minimum and started increasing.

    Returns:
        tuple: (updated min_ke, updated ke_increasing_count, should_exit)
    """
    if previous_ke is None:
        return min_ke, ke_increasing_count, False

    # Update minimum KE if current is lower
    if min_ke is None or kinetic_energy < min_ke:
        return kinetic_energy, 0, False

    # Check if KE is increasing after minimum
    if kinetic_energy > previous_ke:
        ke_increasing_count += 1
        if ke_increasing_count >= 3:
            log_func(
                f"\n Kinetic energy is increasing (min: {min_ke:.3e}, current: {kinetic_energy:.3e})"
            )
            log_func("Stopping analysis - minimum energy state reached.")
            return min_ke, ke_increasing_count, True
    else:
        ke_increasing_count = 0

    return min_ke, ke_increasing_count, False


def _check_completion_status(line: str) -> tuple[bool, bool]:
    """Check if analysis has completed or failed.

    Returns:
        tuple: (has_status, success)
    """
    if "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in line:
        log_func("\n Job completed successfully.")
        return True, True
    elif "ANALYSIS ABORTED" in line or "ANALYSIS TERMINATED" in line:
        log_func("\n Job did not complete successfully.")
        return True, False
    return False, False


def monitor_job(sta_path: str) -> bool:
    """Monitor the status of an Abaqus job until completion.

    Args:
        sta_path: Path to the .sta file of the job to monitor

    Returns:
        bool: True if job completed successfully, False otherwise
    """
    last_printed_line_index = -1
    header_printed = False
    previous_ke = None
    min_ke = None
    ke_increasing_count = 0

    time.sleep(5)  # Initial wait for file creation

    while True:
        try:
            with open(sta_path, "r") as sta_file:
                lines = sta_file.readlines()

            solution_progress_index = _find_solution_progress_section(lines)

            if solution_progress_index >= 0:
                start_index = solution_progress_index + 2

                for i in range(
                    max(start_index, last_printed_line_index + 1), len(lines)
                ):
                    line = lines[i].strip()

                    # Check for completion or errors
                    has_status, success = _check_completion_status(line)
                    if has_status:
                        return success

                    # Skip header lines
                    if _is_header_line(line):
                        last_printed_line_index = i
                        continue

                    # Parse and print increment data
                    if _is_increment_data_line(line):
                        values = line.split()
                        if len(values) >= 7:
                            try:
                                data = _parse_increment_data(values)

                                if not header_printed:
                                    _print_header()
                                    header_printed = True

                                _print_increment_data(data)

                                # Check for KE minimum
                                min_ke, ke_increasing_count, should_exit = (
                                    _check_ke_minimum(
                                        data["kinetic_energy"],
                                        previous_ke,
                                        min_ke,
                                        ke_increasing_count,
                                    )
                                )
                                if should_exit:
                                    return True

                                previous_ke = data["kinetic_energy"]

                            except (ValueError, IndexError):
                                if line:
                                    log_func(line)
                    elif line and not _should_skip_line(line):
                        log_func(line)

                    last_printed_line_index = i

        except FileNotFoundError:
            log_func(
                f"Status file not found: {sta_path}. Waiting for file to be created..."
            )
            time.sleep(5)
            continue

        time.sleep(5)
