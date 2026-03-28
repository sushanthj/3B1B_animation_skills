#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    echo "Usage: ./cleanup.sh [animation_folder]"
    echo ""
    echo "Clean up partial movie files, tex cache, text cache, and pycache."
    echo ""
    echo "  animation_folder  Path to a specific animation folder (e.g. animations/animation_foo)"
    echo "                    If omitted, cleans ALL animation folders under animations/"
    echo ""
    echo "Examples:"
    echo "  ./cleanup.sh                                    # clean all animations"
    echo "  ./cleanup.sh animations/animation_gradient_descent  # clean one animation"
}

cleanup_folder() {
    local dir="$1"
    echo "Cleaning $dir ..."
    rm -rf "$dir"/video/videos/scene/*/partial_movie_files 2>/dev/null || true
    rm -rf "$dir"/video/Tex 2>/dev/null || true
    rm -rf "$dir"/video/texts 2>/dev/null || true
    rm -rf "$dir"/__pycache__ 2>/dev/null || true
    # Also clean any nested pycache
    find "$dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$dir" -type f -name "*.pyc" -delete 2>/dev/null || true
}

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
    exit 0
fi

if [ -n "$1" ]; then
    # Clean specific folder
    if [ ! -d "$1" ]; then
        echo "Error: $1 is not a directory"
        exit 1
    fi
    cleanup_folder "$1"
else
    # Clean all animation folders
    if [ ! -d "$REPO_DIR/animations" ]; then
        echo "No animations/ directory found."
        exit 0
    fi
    for dir in "$REPO_DIR"/animations/animation_*/; do
        [ -d "$dir" ] && cleanup_folder "$dir"
    done
fi

echo "Done."
