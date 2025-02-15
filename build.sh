#!/bin/bash

# Variables
APP_NAME="LibreTranslateGUI"
BIN_PATH="/home/$USER/.local/bin/$APP_NAME"
DESKTOP_FILE="/home/$USER/.local/share/applications/$APP_NAME.desktop"
VENV_DIR="./.venv"
PYTHON_VERSION="3.12.5"  # Ensure this Python version is installed

# Determine the data directory based on the operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    DATA_DIR="$HOME/.local/share/$APP_NAME"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    DATA_DIR="$(cygpath -u "$APPDATA")/$APP_NAME"
else
    DATA_DIR="$HOME/.local/share/$APP_NAME"
fi
ICON_PATH="$DATA_DIR/icon.png"
ICON_URL="https://raw.githubusercontent.com/MrChuw/TranslateGui/refs/heads/main/img/icon.png"


# Step 1: Check if the required Python version is installed
if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
    echo "Python $PYTHON_VERSION is not installed. Installing it with pyenv..."
    pyenv install $PYTHON_VERSION
fi

# Step 2: Create or activate the virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating a new one..."
    python -m venv $VENV_DIR  # Create the virtual environment
    echo "Virtual environment created."
fi

# Activate the virtual environment
echo "Activating the virtual environment..."
source $VENV_DIR/bin/activate

# Step 3: Install required packages
echo "Installing required packages..."
pip install --upgrade pip  # Ensure pip is up-to-date
pip install -r requirements.txt  # Install project dependencies

# Step 4: Build the binary with PyInstaller
echo "Building the binary with PyInstaller..."
pyinstaller --onefile --icon="img/icon.png"  main.py -n $APP_NAME

# Step 5: Create a symbolic link to the binary
if [ -L "$BIN_PATH" ]; then
    echo "Symbolic link already exists at $BIN_PATH. Verifying..."
    if [ "$(readlink -f "$BIN_PATH")" == "$(pwd)/dist/$APP_NAME" ]; then
        echo "Link is valid."
    else
        echo "Link is invalid. Updating it..."
        ln -sf "$(pwd)/dist/$APP_NAME" "$BIN_PATH"
    fi
else
    echo "Creating symbolic link at $BIN_PATH..."
    ln -s "$(pwd)/dist/$APP_NAME" "$BIN_PATH"
fi

# Step 6: Create or update the .desktop file
if [ -f "$DESKTOP_FILE" ]; then
    echo "Desktop file exists. Verifying..."
    if grep -q "Exec=$BIN_PATH" "$DESKTOP_FILE"; then
        echo "Desktop file is valid."
    else
        echo "Desktop file is invalid. Updating it..."
        rm -f "$DESKTOP_FILE"
    fi
fi

if [ ! -f "$DESKTOP_FILE" ]; then
    echo "Creating desktop file at $DESKTOP_FILE..."
    cat << EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=$APP_NAME
Exec=$BIN_PATH
Icon=$ICON_PATH
Terminal=false
Categories=Network;Languages;Office;
EOF
    chmod +x "$DESKTOP_FILE"
fi

# Ensure the data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "Creating data directory at $DATA_DIR..."
    mkdir -p "$DATA_DIR"
fi

# Download the icon if it does not exist
if [ ! -f "$ICON_PATH" ]; then
    echo "Downloading icon from $ICON_URL..."
    curl -o "$ICON_PATH" -L "$ICON_URL"
    if [ $? -ne 0 ]; then
        echo "Failed to download the icon. Please check the URL or your internet connection."
        exit 1
    fi
fi

# Step 7: Final checks
echo "Verifying installation..."
if [ -L "$BIN_PATH" ] && [ -x "$BIN_PATH" ] && [ -f "$DESKTOP_FILE" ]; then
    echo "Build and setup completed successfully!"
else
    echo "There was an issue with the setup. Please check the logs."
fi

# Deactivate the virtual environment
echo "Deactivating the virtual environment..."
deactivate
