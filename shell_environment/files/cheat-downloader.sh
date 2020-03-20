#!/bin/bash
curl -s https://api.github.com/repos/cheat/cheat/releases/latest | grep "cheat-linux-amd64.gz" | cut -d : -f 2,3 | tr -d \" | tail -n 1 | wget -P /tmp -qi -
