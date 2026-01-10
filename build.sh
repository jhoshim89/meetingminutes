#!/bin/bash
set -e

echo "Installing Flutter..."
git clone https://github.com/flutter/flutter.git --depth 1 -b stable flutter-sdk
export PATH="$PATH:$(pwd)/flutter-sdk/bin"

echo "Flutter version:"
flutter --version

echo "Getting dependencies..."
cd flutter_app
flutter pub get

echo "Building web app..."
flutter build web --release

echo "Build complete!"
