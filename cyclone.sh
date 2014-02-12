#!/bin/bash
#
# === Script: cyclone.sh
# 
# This is a shell wrapper to be called from Jenkis.
# It invokes the main python function via fabric.
#
# === Authors
# Marji Cermak <marji@morpht.com>

debug=0

set -e 


if [ "x$debug" == "x1" ]; then

  set -x

  echo $type
  echo $method
  echo $site_id
  echo $provider
  echo $params
  echo $extensions
  echo $notify_url
fi

# All strings need to have "," back-slashed, 
# otherwise fabric will interpret the comma as a parameter delimiter:
provider=${provider//,/\\,}
params=${params//,/\\,}
extensions=${extensions//,/\\,}

# CD to the root of the codebase:
cd $(dirname $0)
echo "Current dir is: $(pwd)"
echo "Running as user $(whoami)"

fab cyclone1:type="${type}",method="${method}",site_id=${site_id},target="${target}",provider="${provider}",params="${params}",extensions="${extensions}",notify_url=${notify_url},token=${token}

echo "End of script."

