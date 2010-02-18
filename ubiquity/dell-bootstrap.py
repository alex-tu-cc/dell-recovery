#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# «dell-bootstrap» - Ubiquity plugin for Dell Factory Process
#
# Copyright (C) 2010, Dell Inc.
#
# Author:
#  - Mario Limonciello <Mario_Limonciello@Dell.com>
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this application; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##################################################################################

from ubiquity.plugin import *
from ubiquity import misc
from threading import Thread, Event
import debconf
import Dell.recovery_common as magic
import subprocess
import os
import re
import gtk
import shutil
import dbus
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

NAME = 'dell-bootstrap'
AFTER = None
BEFORE = 'language'
WEIGHT = 12

#Gtk widgets
class PageGtk(PluginUI):
    def __init__(self, controller, *args, **kwargs):
        self.plugin_widgets = None

        oem = 'UBIQUITY_OEM_USER_CONFIG' in os.environ

        with misc.raised_privileges():
            self.genuine = magic.check_vendor()

        if not oem:
            builder = gtk.Builder()
            builder.add_from_file('/usr/share/ubiquity/gtk/stepDellBootstrap.ui')
            builder.connect_signals(self)
            self.controller = controller
            self.plugin_widgets = builder.get_object('stepDellBootstrap')
            self.automated_recovery = builder.get_object('automated_recovery')
            self.automated_recovery_box = builder.get_object('automated_recovery_box')
            self.interactive_recovery = builder.get_object('interactive_recovery')
            self.interactive_recovery_box = builder.get_object('interactive_recovery_box')
            self.hdd_recovery = builder.get_object('hdd_recovery')
            self.hdd_recovery_box = builder.get_object('hdd_recovery_box')
            self.hidden_radio = builder.get_object('hidden_radio')
            self.reboot_dialog = builder.get_object('reboot_dialog')
            self.reboot_dialog.set_title('Dell Recovery')
            self.info_window = builder.get_object('info_window')
            self.info_window.set_title('Dell Recovery')
            self.info_spinner = builder.get_object('info_spinner')
            if not self.genuine:
                self.interactive_recovery_box.hide()
                self.automated_recovery_box.hide()
                self.automated_recovery.set_sensitive(False)
                self.interactive_recovery.set_sensitive(False)
                builder.get_object('genuine_box').show()

    def plugin_get_current_page(self):
        if not self.genuine:
            self.controller.allow_go_forward(False)
        return self.plugin_widgets

    def get_type(self):
        """Returns the type of recovery to do from GUI"""
        if self.automated_recovery.get_active():
            return "automatic"
        elif self.interactive_recovery.get_active():
            return "interactive"
        else:
            return ""

    def set_type(self,type):
        """Sets the type of recovery to do in GUI"""
        if type == "automatic":
            self.automated_recovery.set_active(True)
        elif type == "interactive":
            self.interactive_recovery.set_active(True)
        else:
            self.hidden_radio.set_active(True)
            if type != "factory":
                self.controller.allow_go_forward(False)
            if type == "hdd":
                self.hdd_recovery_box.show()
                self.interactive_recovery_box.hide()
                self.automated_recovery_box.hide()
                self.interactive_recovery.set_sensitive(False)
                self.automated_recovery.set_sensitive(False)

    def toggle_type(self, widget):
        """Allows the user to go forward after they've made a selection'"""
        self.controller.allow_go_forward(True)

    def show_info_dialog(self):
        self.controller.toggle_top_level()
        self.info_window.show()
        self.info_spinner.start()
        while gtk.events_pending():
            gtk.main_iteration()

    def show_reboot_dialog(self):
        self.info_spinner.stop()
        self.info_window.hide()
        self.reboot_dialog.run()

    def show_exception_dialog(self, e):
        self.info_spinner.stop()
        self.info_window.hide()
        err_dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format='Exception Encountered')
        err_dialog.format_secondary_text(str(e))
        err_dialog.run()
        err_dialog.hide()

class Page(Plugin):
    def __init__(self, frontend, db=None, ui=None):
        self.kexec = True
        self.device = '/dev/sda'
        self.node = ''
        Plugin.__init__(self, frontend, db, ui)

    def install_grub(self):
        """Installs grub on the recovery partition"""
        cd_mount   = misc.execute_root('mount', '-o', 'remount,rw', '/cdrom')
        if cd_mount is False:
            raise RuntimeError, ("CD Mount failed")
        bind_mount = misc.execute_root('mount', '-o', 'bind', '/cdrom', '/boot')
        if bind_mount is False:
            raise RuntimeError, ("Bind Mount failed")
        grub_inst  = misc.execute_root('grub-install', '--force', self.device + '2')
        if grub_inst is False:
            raise RuntimeError, ("Grub install failed")
        unbind_mount = misc.execute_root('umount', '/boot')
        if unbind_mount is False:
            raise RuntimeError, ("Unmount /boot failed")
        uncd_mount   = misc.execute_root('mount', '-o', 'remount,ro', '/cdrom')
        if uncd_mount is False:
            raise RuntimeError, ("Uncd mount failed")

    def disable_swap(self):
        """Disables any swap partitions in use"""
        with open('/proc/swaps','r') as swap:
            for line in swap.readlines():
                if self.device in line or self.node in line:
                    misc.execute_root('swapoff', line.split()[0])
                    if misc is False:
                        raise RuntimeError, ("Error disabling swap on device %s" % line.split()[0])

    def remove_extra_partitions(self):
        """Removes partitions 3 and 4 for the process to start"""
        active = misc.execute_root('sfdisk', '-A2', self.device)
        if active is False:
            self.debug("Failed to set partition 2 active on %s" % self.device)
        for number in ('3','4'):
            remove = misc.execute_root('parted', '-s', self.device, 'rm', number)
            if remove is False:
                raise RuntimeError, ("Error removing partition number: %d on %s" % (number,self.device))

    def boot_rp(self):
        """attempts to kexec a new kernel and falls back to a reboot"""
        shutil.copy('/sbin/reboot', '/tmp')
        if self.kexec and os.path.exists('/cdrom/misc/kexec'):
            shutil.copy('/cdrom/misc/kexec', '/tmp')
        eject = misc.execute_root('eject', '-p', '-m' '/cdrom')
        if eject is False:
            self.debug("Eject was: %d" % eject)

        #Set up a listen for udisks to let us know a usb device has left
        bus = dbus.SystemBus()
        bus.add_signal_receiver(reboot_machine, 'DeviceRemoved', 'org.freedesktop.UDisks')
        
        self.ui.show_reboot_dialog()

        reboot_machine(None)

    def unset_drive_preseeds(self):
        """Unsets any preseeds that are related to setting a drive"""
        for key in [ 'partman-auto/init_automatically_partition',
                     'partman-auto/disk',
                     'partman-auto/expert_recipe',
                     'partman-basicfilesystems/no_swap',
                     'grub-installer/only_debian',
                     'grub-installer/with_other_os',
                     'grub-installer/bootdev',
                     'grub-installer/make_active',
                     'ubiquity/reboot' ]:
            self.db.fset(key, 'seen', 'false')
            self.db.set(key, '')
        self.db.set('ubiquity/partman-skip-unmount', 'false')
        self.db.set('partman/filter_mounted', 'true')

    def fixup_devices(self):
        """Fixes self.device to not be a symlink"""
        #Normally we do want the first edd device, but if we're booted from a USB
        #stick, that's just not true anymore
        if 'edd' in self.device:
            #First read in /proc/mounts to make sure we don't accidently write over the same
            #device we're booted from - unless it's a hard drive
            ignore = ''
            new = ''
            with open('/proc/mounts','r') as f:
                for line in f.readlines():
                    #Mounted
                    if '/cdrom' in line:
                        #and isn't a hard drive
                        device = line.split()[0]
                        if subprocess.call(['/lib/udev/ata_id',device]) != 0:
                            ignore = device
                            break
            if ignore:
                for root,dirs,files in os.walk('/dev/'):
                    for name in files:
                        if name.startswith('sd'):
                            stripped = name.strip('1234567890')
                            if stripped in ignore:
                                continue
                            else:
                                new = stripped
            if new:
                with misc.raised_privileges():
                    #Check if old device already existed:
                    if os.path.islink(self.device):
                        os.unlink(self.device)
                    os.symlink('../../' + new, self.device)
    
        #Follow the symlink
        if os.path.islink(self.device):
            self.node = os.readlink(self.device).split('/').pop()
            self.device = os.path.join(os.path.dirname(self.device), os.readlink(self.device))
        self.debug("Fixed up device we are operating on is %s" % self.device)

    def prepare(self, unfiltered=False):
        try:
            type = self.db.get('dell-recovery/recovery_type')
            #These require interactivity - so don't fly by even if --automatic
            if type != 'factory':
                self.db.set('dell-recovery/recovery_type','')
                self.db.fset('dell-recovery/recovery_type', 'seen', 'false')
            else:
                self.db.fset('dell-recovery/recovery_type', 'seen', 'true')
            self.ui.set_type(type)
        except debconf.DebconfError:
            pass

        try:
            self.kexec = misc.create_bool(self.db.get('dell-recovery/kexec'))
        except debconf.DebconfError:
            pass
        try:
            self.device = self.db.get('partman-auto/disk')
        except debconf.DebconfError:
            pass

        return (['/usr/share/ubiquity/dell-bootstrap'], ['dell-recovery/recovery_type'])

    def run(self, priority, question):
        if question == 'dell-recovery/recovery_type':
            self.fixup_devices()
        return Plugin.run(self, priority, question)

    def ok_handler(self):
        """Copy answers from debconf questions"""
        type = self.ui.get_type()
        self.preseed('dell-recovery/recovery_type', type)
        return Plugin.ok_handler(self)

    def cleanup(self):
        #All this processing happens in cleanup because that ensures it runs for all scenarios
        self.fixup_devices()
        type = self.db.get('dell-recovery/recovery_type')
        # User recovery - need to copy RP
        if type == "automatic":
            self.ui.show_info_dialog()
            self.disable_swap()
            self.rp_builder = rp_builder(self.device, self.kexec)
            self.rp_builder.exit = self.exit_ui_loops
            self.rp_builder.start()
            self.enter_ui_loop()
            self.rp_builder.join()
            if self.rp_builder.exception:
                self.handle_exception(self.rp_builder.exception)
            self.boot_rp()

        # User recovery - resizing drives
        elif type == "interactive":
            self.unset_drive_preseeds()

        # Factory install, post kexec, and booting from RP
        else:
            self.disable_swap()
            self.remove_extra_partitions()
            self.install_grub()
        Plugin.cleanup(self)

    def cancel_handler(self):
        """Called when we don't want to perform recovery'"""
        misc.execute('reboot','-n')

    def handle_exception(self, e):
        self.debug(str(e))
        self.ui.show_exception_dialog(e)

class rp_builder(Thread):
    def __init__(self, device, kexec):
        self.device = device
        self.kexec = kexec
        self.exception = None
        Thread.__init__(self)

    def build_rp(self, cushion=300):
        """Copies content to the recovery partition"""

        def fetch_output(cmd, data=None):
            '''Helper function to just read the output from a command'''
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            (out,err) = proc.communicate(data)
            if proc.returncode is None:
                proc.wait()
            if proc.returncode != 0:
                raise RuntimeError, ("Command %s failed with stdout/stderr: %s\n%s" %
                                     (cmd, out, err))
            return out

        white_pattern = re.compile('/')

        #Calculate UP#
        if os.path.exists('/cdrom/upimg.bin'):
            #in bytes
            up_size = int(fetch_output(['gzip','-lq','/cdrom/upimg.bin']).split()[1])
            #in mbytes
            up_size = up_size / 1048576
        else:
            up_size = 0

        #Calculate RP
        rp_size = magic.white_tree("size", white_pattern, '/cdrom')
        #in mbytes
        rp_size = (rp_size / 1048576) + cushion

        #Zero out the MBR
        with open('/dev/zero','rb') as zeros:
            with misc.raised_privileges():
                with open(self.device,'wb') as out:
                    out.write(zeros.read(1024))

        #Partitioner commands
        data = 'n\np\n1\n\n' # New partition 1
        data += '+' + str(up_size) + 'M\n\nt\nde\n\n' # Size and make it type de
        data += 'n\np\n2\n\n' # New partition 2
        data += '+' + str(rp_size) + 'M\n\nt\n2\n0b\n\n' # Size and make it type 0b
        data += 'a\n2\n\n' # Make partition 2 active
        data += 'w\n' # Save and quit
        with misc.raised_privileges():
            fetch_output(['fdisk', self.device], data)

        #Create a DOS MBR
        with open('/usr/lib/syslinux/mbr.bin','rb')as mbr:
            with misc.raised_privileges():
                with open(self.device,'wb') as out:
                    out.write(mbr.read(404))

        #Restore UP
        if os.path.exists('/cdrom/upimg.bin'):
            with misc.raised_privileges():
                with open(self.device + '1','w') as partition:
                    p1 = subprocess.Popen(['gzip','-dc','/cdrom/upimg.bin'], stdout=subprocess.PIPE)
                    partition.write(p1.communicate()[0])

        #Build RP FS
        fs = misc.execute_root('mkfs.msdos','-n','install',self.device + '2')
        if fs is False:
            raise RuntimeError, ("Error creating vfat filesystem on %s2" % self.device)

        #Mount RP
        mount = misc.execute_root('mount', '-t', 'vfat', self.device + '2', '/boot')
        if mount is False:
            raise RuntimeError, ("Error mounting %s2" % self.device)

        #Copy RP Files
        with misc.raised_privileges():
            magic.white_tree("copy", white_pattern, '/cdrom', '/boot')

        #Install grub
        grub = misc.execute_root('grub-install', '--force', self.device + '2')
        if grub is False:
            raise RuntimeError, ("Error installing grub to %s2" % self.device)

        #Build new UUID
        uuid = misc.execute_root('casper-new-uuid',
                             '/cdrom/casper/initrd.lz',
                             '/boot/casper',
                             '/boot/.disk')
        if uuid is False:
            raise RuntimeError, ("Error rebuilding new casper UUID")

        #Load kexec kernel
        if self.kexec and os.path.exists('/cdrom/misc/kexec'):
            with open('/proc/cmdline') as file:
                cmdline = file.readline().strip('\n').replace('dell-recovery/recovery_type=dvd','dell-recovery/recovery_type=factory').replace('dell-recovery/recovery_type=hdd','dell-recovery/recovery_type=factory')
                kexec_run = misc.execute_root('/cdrom/misc/kexec',
                          '-l', '/boot/casper/vmlinuz',
                          '--initrd=/boot/casper/initrd.lz',
                          '--command-line="' + cmdline + '"')
                if kexec_run is False:
                    self.debug("kexec loading of kernel and initrd failed")

        #Unmount devices
        umount = misc.execute_root('umount', '/boot')

    def exit(self):
        pass

    def run(self):
        try:
            self.build_rp()
        except Exception, e:
            self.exception = e
        self.exit()

def reboot_machine(objpath):
    if os.path.exists('/tmp/kexec'):
        kexec = misc.execute_root('/tmp/kexec', '-e')
        if kexec is False:
            pass

    reboot = misc.execute_root('/tmp/reboot','-n')
    if reboot is False:
        raise RuntimeError, ("Reboot failed")

#Currently we have actual stuff that's run as a late command
#class Install(InstallPlugin):
#
#    def install(self, target, progress, *args, **kwargs):
#        return InstallPlugin.install(self, target, progress, *args, **kwargs)

