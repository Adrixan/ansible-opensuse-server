#!/bin/sh

rsync -rltpog --delete /etc/docker-compose/bitwardenrs/bw-data /home/Adrixan/bw-data/
chown -R Adrixan:users /home/Adrixan/bw-data/

