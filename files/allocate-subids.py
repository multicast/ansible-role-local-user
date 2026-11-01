# SPDX-FileCopyrightText: 2026 Matej Kovac
# SPDX-License-Identifier: MIT

#!/usr/bin/python3
import fcntl
import os
import pwd
import stat
import sys
import tempfile


def login_defs_limits():
    settings = {}
    with open("/etc/login.defs", encoding="utf-8") as source:
        for line in source:
            fields = line.split("#", 1)[0].split()
            if len(fields) == 2 and fields[0] in {
                "SUB_UID_MIN", "SUB_UID_MAX", "SUB_GID_MIN", "SUB_GID_MAX"
            }:
                settings[fields[0]] = int(fields[1])
    limits = {}
    for kind in ("UID", "GID"):
        minimum = settings.get(f"SUB_{kind}_MIN")
        maximum = settings.get(f"SUB_{kind}_MAX")
        if minimum is None or maximum is None or minimum < 0 or maximum < minimum:
            raise ValueError(f"invalid SUB_{kind}_MIN/SUB_{kind}_MAX in /etc/login.defs")
        limits[f"sub{kind.lower()}"] = (minimum, maximum + 1)
    return limits


def read_entries(path):
    try:
        with open(path, encoding="utf-8") as source:
            lines = source.read().splitlines()
    except FileNotFoundError:
        lines = []

    entries = []
    for index, line in enumerate(lines):
        if not line or line.lstrip().startswith("#"):
            continue
        fields = line.split(":")
        if len(fields) != 3 or not fields[0]:
            raise ValueError(f"invalid subordinate ID entry in {path}: {line!r}")
        try:
            start, count = map(int, fields[1:])
        except ValueError as error:
            raise ValueError(f"invalid subordinate ID entry in {path}: {line!r}") from error
        if start < 0 or count <= 0:
            raise ValueError(f"out-of-range subordinate ID entry in {path}: {line!r}")
        entries.append((index, fields[0], start, count))
    return lines, entries


def first_gap(intervals, count, minimum, maximum):
    start = minimum
    for used_start, used_end in sorted(intervals):
        if used_end <= start:
            continue
        if start + count <= used_start:
            break
        start = max(start, used_end)
    if start + count > maximum:
        raise ValueError(f"no subordinate ID range of {count} IDs is available")
    return start


def plan_file(path, name, count, minimum, maximum):
    if count is None:
        return None

    lines, entries = read_entries(path)
    own = [entry for entry in entries if entry[1] == name]
    if len(own) > 1:
        raise ValueError(f"multiple subordinate ID ranges already exist for {name} in {path}")
    others = [entry for entry in entries if entry[1] != name]
    intervals = [(entry[2], entry[2] + entry[3]) for entry in others]

    if own:
        index, _, old_start, _ = own[0]
        if (
            minimum <= old_start
            and old_start + count <= maximum
            and not any(start < old_start + count and old_start < end for start, end in intervals)
        ):
            start = old_start
        else:
            start = first_gap(intervals, count, minimum, maximum)
        replacement = f"{name}:{start}:{count}"
        if lines[index] == replacement:
            return None
        lines[index] = replacement
    else:
        start = first_gap(intervals, count, minimum, maximum)
        lines.append(f"{name}:{start}:{count}")

    return path, lines


def write_file(path, lines):
    try:
        metadata = os.stat(path, follow_symlinks=False)
        mode, owner, group = stat.S_IMODE(metadata.st_mode), metadata.st_uid, metadata.st_gid
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"refusing to replace non-regular file: {path}")
    except FileNotFoundError:
        mode, owner, group = 0o644, 0, 0

    directory = os.path.dirname(path)
    descriptor, temporary = tempfile.mkstemp(prefix=".subid-", dir=directory)
    try:
        os.fchmod(descriptor, mode)
        os.fchown(descriptor, owner, group)
        with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
            destination.write("\n".join(lines) + "\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main():
    if len(sys.argv) != 4:
        raise ValueError("usage: allocate-subids.py NAME SUBUID_COUNT SUBGID_COUNT")
    name = sys.argv[1]
    try:
        pwd.getpwnam(name)
    except KeyError as error:
        raise ValueError(f"{name!r} is not an existing user") from error

    counts = {}
    for kind, value in zip(("subuid", "subgid"), sys.argv[2:]):
        if value:
            counts[kind] = int(value)
            if counts[kind] <= 0:
                raise ValueError(f"{kind} count must be positive")

    if not counts:
        return

    with open("/run/lock/ansible-user-subids.lock", "w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        limits = login_defs_limits()
        plans = [
            plan_file(f"/etc/{kind}", name, counts.get(kind), *limits[kind])
            for kind in ("subuid", "subgid")
        ]
        for plan in plans:
            if plan:
                write_file(*plan)
        print("changed" if any(plans) else "ok")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
