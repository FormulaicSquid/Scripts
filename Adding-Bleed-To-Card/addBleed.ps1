# Function to add bleed to an image file
function addBleed ($inputFileName) {
    # Inform the user about the current file being processed
    echo "Currently working on $inputFileName"

    # Create a new directory 'bleeded_images' if it doesn't exist
    $outputDir = "bleeded_images"
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir
    }

    # Output file name (prepends "bleed_" to the original file name and places it in the 'bleeded_images' folder)
    $outputFileName = "$outputDir\bleed_" + $inputFileName
    echo "The output file name will be $outputFileName"

    # Identify the image dimensions using ImageMagick
    $imageHeight = magick identify -format "%h" $inputFileName
    $imageWidth = magick identify -format "%w" $inputFileName

    # Padding size (set to 72, for example)
    $pad = 72
    echo "pad = $pad, Width = $imageWidth, Height = $imageHeight"

    echo "Creating bleed with $pad px padding for $inputFileName"

    # Step 1: Mirror the image horizontally
    echo " - mirroring horizontally..."
    magick $inputFileName -flop _flopped.$fileExtension

    # Step 2: Create the middle row by appending the original and flipped images
    magick _flopped.$fileExtension $inputFileName _flopped.$fileExtension +append _middle-row.$fileExtension

    # Step 3: Mirror the middle row vertically
    echo " - mirroring vertically..."
    magick _middle-row.$fileExtension -flip _flipped-row.$fileExtension

    # Step 4: Combine the flipped rows with the middle row
    magick _flipped-row.$fileExtension _middle-row.$fileExtension _flipped-row.$fileExtension -append _combined.$fileExtension

    # Step 5: Crop the final combined image to remove extra padding
    echo " - shaving down..."
    $shaveWidth = $imageWidth - $pad
    $shaveHeight = $imageHeight - $pad
    magick _combined.$fileExtension -shave $shaveWidth"x"$shaveHeight "$outputFileName"

    # Step 6: Clean up the temporary files
    echo " - cleaning up..."
    del _flopped.$fileExtension
    del _middle-row.$fileExtension
    del _flipped-row.$fileExtension
    del _combined.$fileExtension
}

# Set the file extension you want to process (e.g., jpeg, png, etc.)
$fileExtension = "png"

# Get all files in the current directory with the specified file extension
$array = (Get-ChildItem -Path . | Where-Object { $_.Name -match "\.$fileExtension$" }).Name

# Process each file with the specified file extension
foreach ($fileName in $array) {
    addBleed $fileName
}
