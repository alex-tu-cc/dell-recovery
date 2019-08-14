#!/bin/sh -e

#Dell factory GRUB2 builder

# TARGET specifies where the binaries will end up
# SOURCE_GRUBDIR is where the conf files used are stored
# TARGET_GRUBCFG is where the main grubcfg will be placed after modification

[ -n "$TARGET" ]         || TARGET=/var/lib/dell-recovery
[ -n "$SOURCE_GRUBDIR" ] || SOURCE_GRUBDIR=/usr/share/dell/grub
[ -n "$TARGET_GRUBCFG" ] || TARGET_GRUBCFG=$TARGET/grub.cfg
echo "Creating factory grub.cfg"
OS=$(lsb_release -s -d)
sed "s,#OS#,$OS,; /#UUID#/d" \
        $SOURCE_GRUBDIR/recovery_partition.cfg \
        > $TARGET_GRUBCFG
