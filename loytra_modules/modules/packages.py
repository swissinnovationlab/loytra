from loytra_modules._loytra_packager import PackagerUserGroup, PackagerUdevRule, PackagerRepo, MultiPackager, PackagerPip

user_group_uucp = PackagerUserGroup("user_group_uucp", "uucp")
user_group_network = PackagerUserGroup("user_group_network", "network")
udev_rule_epaper_acep_generic = PackagerUdevRule("udev_rule_epaper_acep_generic", "/etc/udev/rules.d/99-usb-epaper-acep_generic.rules", 'SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="8957", MODE="0666"')
udev_rule_udisks2 = PackagerUdevRule("udev_rule_udisks2", "/etc/udev/rules.d/99-udisks2.rules", 'ENV{ID_FS_USAGE}=="filesystem|other|crypto", ENV{UDISKS_FILESYSTEM_SHARED}="1"')
user_group_storage = PackagerUserGroup("user_group_storage", "storage")
repo_udisks2 = PackagerRepo("repo_udisks2", "extra/udisks2", "udisks2")
repo_imagemagick = PackagerRepo("repo_imagemagick", "extra/imagemagick", "imagemagick")
repo_lshw = PackagerRepo("repo_lshw", "community/lshw", "lshw")
python_opencv = MultiPackager("python_opencv", [PackagerRepo("repo_python_opencv", "extra/python-opencv", "python-opencv"), PackagerPip("pip_python_opencv", package='opencv-python', module='cv2')])
python_zigpy = PackagerPip("python_zigpy", "zigpy", "zigpy")
python_zigpy_deconz = PackagerPip("python_zigpy_deconz", "zigpy-deconz", "zigpy_deconz")
python_zha_quirks = PackagerPip("python_zha_quirks", "zha-quirks", "zhaquirks")
