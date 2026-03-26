#!/bin/bash

# This is the lowest version of pip that supports --build-constraint option.
pip install 'pip==25.3'
pip install "$@"
