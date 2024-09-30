# Image Bleed Script

This PowerShell script automatically adds a "bleed" to image files by mirroring the edges of the image. Bleed is typically used in printing to extend the image beyond its borders to avoid unwanted white spaces during trimming.

The script processes all image files of a specified extension in the current directory and outputs the modified versions with a bleed effect.

## Features

- Automatically detects image dimensions using ImageMagick.
- Adds a mirrored bleed effect around the image.
- Supports multiple file formats such as JPEG, PNG, and more (based on your input).
- Cleans up temporary files created during the process.
- Customizable padding (default is set to 144px).

## Prerequisites

Before running the script, make sure the following are installed:

1. **PowerShell**:
   - Windows: Pre-installed on most systems.
   - macOS/Linux: Install via [Microsoft’s installation guide](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell).

2. **ImageMagick**:
   - Install ImageMagick from [here](https://imagemagick.org/script/download.php).
   - Ensure ImageMagick is added to your system’s PATH so that the `magick` command is accessible from PowerShell.

## Usage

### 1. Clone the Script

Download or clone this repository to your local machine. Place the script in a directory where your image files are located.

### 2. Set the Desired File Extension

Inside the script, you can define the file extension you want to process. For example, to process PNG files, set:

```powershell
$fileExtension = "png"
```
By default, the script is set to process JPEG files:

```powershell
$fileExtension = "jpeg"
```
### 3. Run the Script
Open PowerShell and navigate to the folder where the script and image files are located:

```bash
cd C:\path\to\your\directory
```
Run the script:

```bash
.\addBleed.ps1
```

The script will process all files with the specified extension in the current directory and generate new files with the prefix bleed_.

### 4. Adjust Padding (Optional)
By default, the script adds a 144-pixel padding to each side of the image. If you wish to adjust this, locate the following line in the script:

```powershell
$pad = 144
```
Change the value 144 to your desired padding size.

Example Directory Structure
```plaintext
your-folder/
│
├── addBleed.ps1
├── image1.jpeg
├── image2.jpeg
└── bleed_image1.jpeg  # Created after running the script
└── bleed_image2.jpeg  # Created after running the script
```
## Cleaning Up
The script will automatically delete the temporary files it generates during processing. Your directory will only contain the original and modified images.

## Troubleshooting
### Execution Policy Error
If you encounter an error about script execution policies, you might need to change the execution policy in PowerShell. Run this command to allow script execution:

```bash
Set-ExecutionPolicy RemoteSigned
```

### ImageMagick Command Not Found
If PowerShell cannot find the magick command, ensure ImageMagick is installed correctly and added to your system’s PATH. Reinstall if necessary.

## License
This script is open-source and freely available for personal or commercial use. Feel free to modify or distribute it.

```markdown
### Explanation:
- The **Prerequisites** section ensures users have both PowerShell and ImageMagick installed.
- The **Usage** section explains how to customize the file extension, set the padding, and run the script.
- A **Troubleshooting** section is added to address common issues like PowerShell execution policy errors and missing ImageMagick commands.
- The **License** section leaves room for the script to be freely used or modified.
```

Let me know if you'd like further changes!