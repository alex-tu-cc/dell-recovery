TOPDIR	?= $(shell pwd)/..
INSTALL         ?= install
MAKE            ?= make
CC              = $(CROSS_COMPILE)gcc
LD              = $(CROSS_COMPILE)ld
OBJCOPY         = $(CROSS_COMPILE)objcopy
READELF         = eu-readelf
ARCH            = $(shell $(CC) -dumpmachine | cut -f1 -d- | sed s,i[3456789]86,ia32,)
GNUEFIDIR	= /usr/lib

CFLAGS		?= -O0 -g3
BUILDFLAGS	:= $(CFLAGS) -fpic -Wall -fshort-wchar \
	-fno-strict-aliasing -fno-merge-constants -ffreestanding \
	-fno-stack-protector -fno-stack-check --std=c11 -DCONFIG_$(ARCH) \
	-I/usr/include/efi/ -I/usr/include/efi/$(ARCH)/ \
	-iquote$(TOPDIR)/include "-DDEBUGDIR=L\"$(DEBUGDIR)/\""
CCLDFLAGS	?= -nostdlib -Wl,--warn-common \
	-Wl,--no-undefined -Wl,--fatal-warnings \
	-Wl,-shared -Wl,-Bsymbolic -L$(LIBDIR) -L$(GNUEFIDIR) \
	-Wl,--build-id=sha1 -Wl,--hash-style=sysv \
	$(GNUEFIDIR)/crt0-efi-$(ARCH).o
OBJCOPY_GTE224 = $(shell expr `$(OBJCOPY) --version |grep ^"GNU objcopy" | sed 's/^.* //g' | cut -f1-2 -d.` \>= 2.24)


FORMAT = --target efi-app-x86_64
BUILDFLAGS += -mno-mmx -mno-sse -mno-red-zone -nostdinc \
		-maccumulate-outgoing-args -DEFI_FUNCTION_WRAPPER \
		-DGNU_EFI_USE_MS_ABI -I$(shell $(CC) -print-file-name=include)

TARGETS = MokSBStateSet.efi

all : $(TARGETS)

.SECONDARY: $(foreach target,$(TARGETS),$(target).debug $(target).build-id)

%.efi : %.so
ifneq ($(OBJCOPY_GTE224),1)
	$(error objcopy >= 2.24 is required)
endif
	$(OBJCOPY) -j .text -j .sdata -j .data -j .dynamic -j .dynsym \
		-j .rel* -j .rela* -j .reloc -j .eh_frame \
		$(FORMAT) $^ $@

%.efi.debug : %.so
ifneq ($(OBJCOPY_GTE224),1)
	$(error objcopy >= 2.24 is required)
endif
	$(OBJCOPY) -j .text -j .sdata -j .data -j .dynamic -j .dynsym \
		-j .rel* -j .rela* -j .reloc -j .eh_frame \
		-j .debug* -j .note.gnu.build-id \
		$^ $@

%.efi.build-id : %.so
	$(READELF) -n $^ | grep "Build ID:" | \
		sed -e 's/^.*Build ID: //' -e 's,^\(..\),\1/,' > $@

%.so : %.o
	$(CC) $(CCLDFLAGS) -o $@ $^ -lefi -lgnuefi \
		$(shell $(CC) -print-libgcc-file-name) \
		-T elf_$(ARCH)_efi.lds

%.o : %.c
	$(CC) $(BUILDFLAGS) -c -o $@ $^

clean :
	@rm -vf $(TARGETS) *.o *.so *.efi.signed *.efi *.efi.debug \
		*.efi.build-id
