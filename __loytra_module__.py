from loytra_modules import LoytraModule, Moduler

__loytra_module__ = [
    # loytra
    LoytraModule(
        module_name="loytra",
        moduler=Moduler(package="loytra_cli",
                        module="loytra_cli",
                        hash="main",
                        url="github.com/swissinnovationlab/loytra"),
        sort_index=0
    ),
]
