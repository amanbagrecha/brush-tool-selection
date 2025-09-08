#!/bin/sh

# Package the plugin as a ZIP archive excluding docs and other non-plugin files.
# Usage: sh package.sh

set -e

git archive --format=zip --prefix=brush_selection_tool/ -o brush_selection_tool.zip HEAD
