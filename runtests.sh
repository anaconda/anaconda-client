#!/bin/bash
# Install nose, freezegun, nose-progressive, and watchdog
watchmedo shell-command -R -p "*.py" \
  -c "nosetests --with-progressive"