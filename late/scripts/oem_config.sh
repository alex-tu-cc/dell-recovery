#!/bin/sh
#
#       <oem_config.sh>
#
#        Setup the early env before oem config or cleanup after
#
#       Copyright 2010-2011 Dell Inc.
#           Mario Limonciello <Mario_Limonciello@Dell.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
# vim:ts=8:sw=8:et:tw=0
#

# $1 -> early/late
#
# for early:
# $2 -> /cdrom or /isodevice

DEVICE=$(python3 << EOF
from Dell.recovery_common import find_partition
print(find_partition().decode('utf-8'))
EOF
)

if [ "$1" = "early" ]; then
    mkdir -p $2
    mount $DEVICE $2
    if [ -f $2/.disk/info.recovery -a ! -f $2/.disk/info ]; then
        cp $2/.disk/info.recovery $2/.disk/info
    fi
    if [ -f "$2/factory/grubenv" ]; then
        grub-editenv $2/factory/grubenv unset install_finished
    fi
    mount -o remount,ro $2
    if [ -f "$2/ubuntu.iso" ]; then
        mount -o loop $2/ubuntu.iso /cdrom
    fi
    /usr/share/dell/scripts/pool.sh
elif [ "$1" = "late" ]; then
    if [ -d "/isodevice" ]; then
        umount /isodevice
        rm -rf /isodevice
    fi
    mount $DEVICE /cdrom
    if [ -f /cdrom/.disk/info.recovery -a -f /cdrom/.disk/info ]; then
        rm -f /cdrom/.disk/info
    fi
    umount /cdrom
    /usr/share/dell/scripts/pool.sh cleanup

    BOOTNUMS=$(efibootmgr | sed '/MokSBStateSet/!d; s,\* .*,,; s,Boot,,')
    for BOOTNUM in $BOOTNUMS;
    do
        if [ -n "$BOOTNUM" ]; then
            efibootmgr -b "$BOOTNUM" -B
        fi
    done
    #if this was installed to work around secure boot, clean it up
    rm -f /boot/efi/EFI/ubuntu/MokSBStateSet.efi
else
    echo "Unknown arguments $1 $2"
fi
