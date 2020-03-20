#!/bin/bash
curl -s curl -s https://api.github.com/repos/r-darwish/topgrade/releases/latest | grep "x86_64" | cut -d : -f 2,3 | tr -d \" | tail -n 1 | wget -O /tmp/topgrade.tar.gz -qi -
