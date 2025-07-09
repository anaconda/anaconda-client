#!/bin/bash -e
set -e
echo

conda 1> /dev/null 2>&1 || (echo -e "It looks like you don't have conda installed or activated\\n\\nPlease refer to https://docs.conda.io/en/latest/miniconda.html to find installer of the latest version, if you don't have one installed yet.\\n" && exit 1)
expect -v 1> /dev/null 2>&1 || (echo -e "You should have 'expect' installed in your system.\\n" && exit 1)

[ "$TST_CMD" != "" ] || export PYTHONPATH="../" TST_CMD="python -W ignore -m binstar_client.scripts.cli"
echo -e "Using '${TST_CMD}' as an anaconda command.\\nYou may change it by providing TST_CMD=... environment variable.\\n"

[ "${TST_LOGIN}" != "" ] || read -r -p "Anaconda login: " TST_LOGIN
[ "${TST_PASSWORD}" != "" ] || read -r -s -p "Anaconda password: " TST_PASSWORD
echo

echo -e "/?\\\\ Checking current anaconda-client version:\\n"
${TST_CMD} --version
echo

echo -e "/?\\\\ Checking config:\\n"

${TST_CMD} config --files 1>/dev/null 2>&1 || (echo -e "\\n\\n/!\\\\ Listing of configuration files test failed.\\n" && exit 1)
${TST_CMD} config --show 1>/dev/null 2>&1 || (echo -e "\\n\\n/!\\\\ Configuration presentation test failed.\\n" && exit 1)

echo -e "/?\\\\ Login:\\n"
echo -e "spawn ${TST_CMD} login\\nexpect {\\n  \"Username: \" {\\n    send -- \"${TST_LOGIN}\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  \"Password: \" {\\n    send -- \"${TST_PASSWORD}\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  \"Password: \" {\\n    send_user \"\\\\nInvalid username/password.\"\\n    exit 67\\n  }\\n  \"Would you like to continue \" {\\n    send -- \"y\\\\r\"\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Login test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Upload package:\\n"
${TST_CMD} upload ./data/conda_gc_test-1.2.1-3.tar.bz2 || (echo -e "\\n\\n/!\\\\ Upload package test failed.\\n" && exit 1)
echo

${TST_CMD} upload ./data/bcj-cffi-0.5.1-py310h295c915_0.tar.bz2 || (echo -e "\\n\\n/!\\\\ Upload package test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Update package:\\n"
${TST_CMD} update "${TST_LOGIN}/conda_gc_test" ./data/conda_gc_test_metadata.json || (echo -e "\\n\\n/!\\\\ Update package test failed.\\n" && exit 1)
echo

${TST_CMD} update "${TST_LOGIN}/bcj-cffi" ./data/conda_gc_test_metadata.json || (echo -e "\\n\\n/!\\\\ Update package test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Download package:\\n"
rm -rf pkg_tmp
mkdir -p pkg_tmp/noarch pkg_tmp/linux-64
${TST_CMD} download "${TST_LOGIN}/conda_gc_test" -o pkg_tmp || (echo -e "\\n\\n/!\\\\ Download package test failed.\\n" && exit 1)
[ $(find pkg_tmp -name conda_gc_test-1.2.1-3.tar.bz2 | wc -l) = 1 ] || (echo -e "\\n\\n/!\\\\ Download package test failed.\\n" && exit 1)
rm -rf pkg_tmp
echo

rm -rf pkg_tmp
mkdir -p pkg_tmp/noarch pkg_tmp/linux-64
${TST_CMD} download "${TST_LOGIN}/bcj-cffi" -o pkg_tmp || (echo -e "\\n\\n/!\\\\ Download package test failed.\\n" && exit 1)
[ $(find pkg_tmp -name bcj-cffi-0.5.1-py310h295c915_0.tar.bz2 | wc -l) = 1 ] || (echo -e "\\n\\n/!\\\\ Download package test failed.\\n" && exit 1)
rm -rf pkg_tmp
echo

echo -e "/?\\\\ Remove package:\\n"
echo -e "spawn ${TST_CMD} remove \"${TST_LOGIN}/conda_gc_test\"\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove package test failed.\\n" && exit 1)
echo

echo -e "spawn ${TST_CMD} remove \"${TST_LOGIN}/bcj-cffi\"\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove package test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Copy package:\\n"
${TST_CMD} copy --from-label main --to-label test anaconda/pip/21.2.4 || (echo -e "\\n\\n/!\\\\ Copy package test failed.\\n" && exit 1)
echo

${TST_CMD} copy --from-label main --to-label test anaconda/git-lfs/2.13.3 || (echo -e "\\n\\n/!\\\\ Copy package test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Move package:\\n"
${TST_CMD} move --from-label test --to-label demo "${TST_LOGIN}/pip/21.2.4" || (echo -e "\\n\\n/!\\\\ Move package test failed.\\n" && exit 1)
echo

${TST_CMD} move --from-label test --to-label demo "${TST_LOGIN}/git-lfs/2.13.3" || (echo -e "\\n\\n/!\\\\ Move package test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Download copied package:\\n"
rm -rf pkg_tmp
mkdir -p pkg_tmp/linux-32 pkg_tmp/linux-64 pkg_tmp/linux-aarch64 pkg_tmp/linux-ppc64le pkg_tmp/linux-s390x pkg_tmp/noarch pkg_tmp/osx-64 pkg_tmp/osx-arm64 pkg_tmp/win-32 pkg_tmp/win-64
${TST_CMD} download "${TST_LOGIN}/pip" -o pkg_tmp || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
[ $(find pkg_tmp -name 'pip-21.2.4-*.tar.bz2' | wc -l) ">" 0 ] || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
rm -rf pkg_tmp
echo

rm -rf pkg_tmp
mkdir -p pkg_tmp/linux-32 pkg_tmp/linux-64 pkg_tmp/linux-aarch64 pkg_tmp/linux-ppc64le pkg_tmp/linux-s390x pkg_tmp/noarch pkg_tmp/osx-64 pkg_tmp/osx-arm64 pkg_tmp/win-32 pkg_tmp/win-64
${TST_CMD} download "${TST_LOGIN}/git-lfs" -o pkg_tmp || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
[ $(find pkg_tmp -name 'git-lfs-2.13.3-*.tar.bz2' | wc -l) ">" 0 ] || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
rm -rf pkg_tmp
echo

echo -e "/?\\\\ Remove copied package:\\n"
echo -e "spawn ${TST_CMD} remove ${TST_LOGIN}/pip\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove copied package test failed.\\n" && exit 1)
echo

echo -e "spawn ${TST_CMD} remove ${TST_LOGIN}/git-lfs\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove copied package test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Logout:\\n"
${TST_CMD} logout || (echo -e "\\n\\n/!\\\\ Logout test failed.\\n" && exit 1)
echo

echo -e "/?\\\\ Success!\\n\\nAll tests have passed!\\n"

rm -rf ./linux-32 ./linux-64 ./linux-aarch64 ./linux-ppc64le ./linux-s390x ./noarch ./osx-64 ./osx-arm64 ./win-32 ./win-64
