import os


def make_backup(filename):
    if os.path.exists(filename):
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)

        # make backup subdir if it does not exist
        backup_dir = os.path.join(dirname, "backup")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Remove old backup suffixed with '9' if it exists
        backup_file = os.path.join(backup_dir, basename)
        if os.path.exists(backup_file + "9"):
            os.remove(backup_file + "9")

        # Shift backups
        for i in range(9, -1, -1):
            old_suffix = f".{i - 1}" if i > 0 else ""
            if os.path.exists(backup_file + old_suffix):
                os.rename(backup_file + old_suffix, f"{backup_file}.{i}")

        # Make new backup
        os.rename(filename, backup_file)
