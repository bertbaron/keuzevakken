# Creates a distribution zip archive including the examples
import os
import subprocess


class Platform:
    WINDOWS = 'windows'
    LINUX = 'linux'
    MACOS = 'macos'


def main():
    platform = determine_platform()
    print(f"Detected platform: {platform}")
    copy_examples(platform)
    create_archive(platform)


def determine_platform():
    """Determines the platform and returns it as a string"""
    if os.name == 'nt':
        return Platform.WINDOWS
    elif os.name == 'posix':
        if 'darwin' in os.uname().sysname.lower():
            return Platform.MACOS
        else:
            return Platform.LINUX
    else:
        raise ValueError("Unsupported platform")


def copy_examples(platform):
    """Copies the ./examples directory to the ./dist directory"""

    if platform == Platform.WINDOWS:
        run_cmd(['xcopy', '/E', '/I', 'examples', 'dist'])
    else:
        run_cmd(['cp', '-r', 'examples', 'dist'])


def create_archive(platform):
    target = os.getenv('TARGET', '..')
    print(f"Creating archive for {target}")

    if platform == Platform.WINDOWS:
        run_cmd(['7z', 'a', f'keuzevakken-{target}.zip', 'dist\\*'], cwd='dist')
    else:
        if platform == Platform.MACOS and os.path.exists('dist/keuzevakken'):
            run_cmd(['rm', '-rf', 'dist/keuzevakken'])

        run_cmd(['zip', '-r', f'keuzevakken-{target}.zip', '.'], cwd='dist')


def run_cmd(cmd, cwd=None):
    print(f"Running {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)


if __name__ == "__main__":
    main()
