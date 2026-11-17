# SWARM — Installation requirements for Linux, macOS and Windows
### Table of Contents
* Check out the [Linux](#linux-section) environment notes.
* Check out the [macOS](#macos-section) environment notes.
* Check out the [Windows](#windows-section) environment notes.

SWARM is currently distributed as Python source code, not as a self-contained executable yet. Users therefore need Python, the required Python libraries, and FFmpeg installed on their computer.

The installation order matters because the launchers start SWARM using an already-installed Python interpreter.
<hr>
<a id="linux-section"></a>
## Linux
(Mint, Ubuntu, and Debian based OS)

Recommended installation method

Use the Linux distribution's package manager. This installs Python, Tkinter, NumPy, Matplotlib and FFmpeg in an environment that works with your `.desktop` launcher. Matplotlib also documents that some Linux systems require a separate Tkinter package.
<br><br>
### Step 1 — Install the required components

Open a terminal and run:
<blockquote>
<b>Note:</b>
<br>
python3 is standard on Linux, while Linux Mint pre-installs tk and numpy. The command below installs only the missing dependencies.
<br>
Do not install NumPy or Matplotlib separately via pip.
<br>
</blockquote>

```
sudo apt install python3 python3-tk python3-numpy python3-matplotlib ffmpeg
```

These are the required components:

| Component     | Purpose                                                     |
| ------------- | ----------------------------------------------------------- |
| Python 3      | Runs SWARM                                                  |
| Tkinter       | Provides the graphical interface                            |
| NumPy         | Processes audio sample data                                 |
| Matplotlib    | Renders the waveform images                                 |
| FFmpeg        | Decodes audio and embeds artwork in supported audio formats |

<br>
### Step 2 — Verify the installation

Run:

```
python3 --version
ffmpeg -version
python3 -c "import tkinter, numpy, matplotlib; print('SWARM dependencies OK')"
```

You should see the Python and FFmpeg version information, followed by:

```
SWARM dependencies OK
```
If the Python import test fails, resolve that problem before launching SWARM.
<br><br>
### Step 3 — Place and launch SWARM

Keep `SWARM_Linux.desktop` in the same directory as `main.py`, along with the rest of the SWARM files.

If Linux asks you to trust the launcher, select Allow Launching.
<br><br>
### Optional packages

> #### Pillow — image support and resizing

Pillow enables resizing of images in Help documents and supports artwork-resizing functionality. Without it, the current Help renderer can display PNG images at their native size, but cannot resize them; some other image formats will not display.

```
sudo apt install python3-pil
```


> #### Mutagen — artwork embedding for OGG/OGA and AIFF audio files

Check the version available in your distribution:

```
apt-cache policy python3-mutagen
```

Install the package if Mutagen is not installed and you use OGG/OGA and AIFF audio files

```
sudo apt install python3-mutagen
```

Without a suitable Mutagen version, normal waveform generation still works, but embedding cover artwork in OGG/OGA and AIFF is unavailable. Other supported artwork operations use FFmpeg.
<br><br>
### Extra — Linux

These commands are specifically for Linux Mint and other Debian/Ubuntu-based distributions. Fedora, Arch Linux and other distributions use different package names and package managers.

#### Drag & Drop

No additional installation is required. SWARM includes its own drag-and-drop library (TkinterDnD2) and the native Linux runtime files.

You can drop a supported audio file or a folder onto the SWARM window to update the active path. If an operation is already running, SWARM refuses the drop to prevent accidental changes to the active processing path.
<br><br>
<a id="macos-section"></a>
## macOS

The macOS launcher needs to find the correct Python interpreter and its installed libraries. Python.org's installers include a suitable Tcl/Tk version for Tkinter; Homebrew also supplies Python and FFmpeg.
<br><br>
### Step 1 — Install Python

For the most reproducible baseline, use a 64-bit Python 3.12 installation.

Download it from the official Python website:

[Python downloads for macOS](https://www.python.org/downloads/macos/)

Use the installer appropriate for the Mac's processor, such as the universal2 installer when available. Avoid relying on Apple's system-provided Python for SWARM's Tkinter interface.
<br><br>
### Step 2 — Install FFmpeg

The simplest route, when Homebrew is available, is:

```
brew install ffmpeg
```
Homebrew's official FFmpeg formula supports this command.

If Homebrew is not installed, see the [official Homebrew installation instructions](https://docs.brew.sh/Installation). FFmpeg also provides links to precompiled builds for macOS on its [download page](https://www.ffmpeg.org/download.html).
<br><br>
### Step 3 — Install SWARM's required Python libraries

Open Terminal and run:

```
python3 -m pip install --upgrade pip
python3 -m pip install numpy matplotlib
```

These are the required third-party Python packages. Matplotlib provides prebuilt packages for macOS and documents installation through `pip`.


Important: the current `SWARM_macOS.app` launcher checks for a project-local `.venv` first, then searches for Homebrew Python before the Python.org installation. If Homebrew Python is present, install the libraries into that interpreter rather than a different Python copy.

For example, on Apple Silicon, when the launcher uses Homebrew Python:

```
/opt/homebrew/bin/python3 -m pip install numpy matplotlib
```

On an Intel Mac using Homebrew's standard prefix:

```
/usr/local/bin/python3 -m pip install numpy matplotlib
```

Use the command matching the interpreter the launcher will actually select.
<br><br>
### Step 4 — Verify the installation

Run these commands using the same Python interpreter selected above:

```
python3 -c "import tkinter, numpy, matplotlib; print('SWARM dependencies OK')"
ffmpeg -version
```

If the Python command does not target the interpreter used by the launcher, run the checks with that interpreter's full path instead.
<br><br>
### Step 5 — Launch SWARM

Double-click `SWARM_macOS.app` beside `main.py`.

The launcher runs SWARM without opening Terminal. If macOS blocks the unsigned launcher, the user may need to approve it through the usual macOS security controls.
<br><br>
### Optional packages

> #### Pillow — Help images and artwork resizing

```
python3 -m pip install Pillow
```

> #### Mutagen — OGG/OGA and AIFF artwork embedding

```
python3 -m pip install "mutagen>=1.47.0"
```

Run these commands using the same Python interpreter that the `.app` launcher uses. Pillow provides prebuilt packages for macOS, while Mutagen is available through PyPI.
<br><br>
### Regarding macOS
<br>
**Drag and drop**
No additional installation is required. SWARM includes its own drag-and-drop library (TkinterDnD2) and the native macOS runtime files. 

Users can drop a supported audio file or a folder onto the SWARM window to update the active path. If an operation is already running, SWARM refuses the drop to prevent accidental changes to the active processing path.

You do not need to install Tkinter separately when using a current Python.org installer that includes Tcl/Tk.

> **macOS Launcher Testers Needed!** 
> <br>
>I develop entirely in Linux environment and am currently **Rayo's Number of parsecs away from macOS**. Because I cannot test the macOS launcher locally, **cross-platform testers and PRs are highly appreciated!**
<br><br>

<a id="windows-section"></a>
## Windows

### Step 1 — Install Python

Install 64-bit Python >=3.12 from the official website:

[Python downloads for Windows](https://www.python.org/downloads/windows/)

Use a normal Python installation rather than the minimal embeddable distribution. Make sure Python's Tcl/Tk support, `pip`, and the Python launcher are available. The official Windows documentation distinguishes the windowed launchers `pyw` and `pythonw` from their console counterparts.



### Step 2 — Install FFmpeg

On a current Windows 10 or Windows 11 computer with `winget`, open PowerShell and run:

```
winget install -e --id Gyan.FFmpeg
```

The package is a precompiled FFmpeg build from Gyan. The official FFmpeg download page links to Windows builds including Gyan's builds.

If `winget` is unavailable, use the Windows builds linked from the [official FFmpeg download page](https://www.ffmpeg.org/download.html). 
Follow the build's instructions to **make `ffmpeg.exe` available through `PATH`.**

After installation, open a new PowerShell window and run:

```
ffmpeg -version
```

If you get a version number, you're in.

### Step 3 — Install SWARM's required Python libraries

Open PowerShell and run:

```
py -3 -m pip install --upgrade pip
py -3 -m pip install numpy matplotlib
```

The `py -3` command installs the libraries into the default Python 3 environment selected by the Python launcher, matching the version the SWARM Windows launcher normally requests.

### Step 4 — Verify the installation

Run:

```
py -3 -c "import tkinter, numpy, matplotlib; print('SWARM dependencies OK')"
ffmpeg -version
```

The first command should print `SWARM dependencies OK`.

### Step 5 — Launch SWARM

Keep `SWARM_Windows.vbs` beside `main.py` and double-click the `.vbs` file. It attempts to use `pyw` first, then `pythonw`, so it can launch SWARM without a console window.

### Optional packages

#### Pillow — Help images and artwork resizing

```
py -3 -m pip install Pillow
```

#### Mutagen — OGG/OGA and AIFF artwork embedding

```
py -3 -m pip install "mutagen>=1.47.0"
```

Pillow and Mutagen are optional Python packages. Their installation details are documented by the projects.


### Windows-Specific Notes

**Drag and drop**
No additional installation is required. SWARM includes its own drag-and-drop library (TkinterDnD2) and the native Windows runtime files. Users can drop a supported audio file or a folder onto the SWARM window to update the active path. If an operation is already running, SWARM refuses the drop to prevent accidental changes to the active processing path.

- Python needs to be installed with Tkinter support; do not try to install Tkinter using `pip`.
- Do not use the minimal embeddable Python package for this setup.


> **Windows Launcher Testers Needed!** 
> <br>
> I develop entirely in Linux environment and am currently a **googolplex parsecs away from a Windows OS**. Because I cannot test the Windows launcher locally, **cross-platform testers and PRs are highly appreciated!**


## Which components are actually required?<br>

| Component        | Linux                                 | macOS                                          | Windows                                  |
| ---------------- | ------------------------------------- | ---------------------------------------------- | ---------------------------------------- |
| Python 3         | Required                              | Required                                       | Required                                 |
| Tkinter          | `python3-tk` package                  | Included with recommended Python.org installer | Included with normal Python installation |
| NumPy            | Required                              | Required                                       | Required                                 |
| Matplotlib       | Required                              | Required                                       | Required                                 |
| FFmpeg           | Required                              | Required                                       | Required                                 |
| Pillow           | Optional, recommended                 | Optional, recommended                          | Optional, recommended                    |
| Mutagen ≥ 1.47.0 | Optional, version availability varies | Optional                                       | Optional                                 |


