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
        run_cmd(['xcopy', '/E', '/I', 'examples', 'dist\\examples'])
    else:
        run_cmd(['cp', '-r', 'examples', 'dist'])


def create_archive(platform):
    print(f"Creating archive for {platform}")

    if platform == Platform.WINDOWS:
        run_cmd(['powershell', '-Command', 'Compress-Archive -Path .\\* -DestinationPath keuzevakken.zip'], cwd='dist')
    else:
        # When building a .app for macOs, pyinstaller leaves the keuzevakken directory
        if platform == Platform.MACOS and os.path.isdir('dist/keuzevakken'):
            run_cmd(['rm', '-rf', 'dist/keuzevakken'])

        run_cmd(['zip', '-r', f'keuzevakken.zip', '.'], cwd='dist')


def run_cmd(cmd, cwd=None):
    print(f"Running {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)


if __name__ == "__main__":
    main()
